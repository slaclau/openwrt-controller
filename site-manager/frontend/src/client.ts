import { client as controllerClient } from 'openwrt-controller/src/sdk/client.gen.ts'
import { client as siteManagerClient } from './sdk/client.gen.ts'
import { refreshTokenAuthRefreshPost } from './sdk'
import { ref, type Ref } from 'vue'
import { assert } from '@vueuse/core'
import { ElNotification } from 'element-plus'
import router from './router'
import type { DcMessage } from './views/SiteView.vue'

export const dataChannel: Ref<RTCDataChannel | null> = ref(null)

const pendingRequests = new Map()

function sendRequest(
  resource: RequestInfo | URL,
  options: RequestInit | undefined,
): Promise<Response> {
  return new Promise((resolve, reject) => {
    // Ensure the channel is actually open
    if (dataChannel.value?.readyState !== 'open') {
      console.warn('WebRTC data channel is not open yet')
      return reject(new Error('WebRTC data channel is not open yet'))
    }

    // Generate a unique ID for correlation
    const requestId = crypto.randomUUID()

    // Set up a timeout so the promise doesn't hang forever
    const timeoutId = setTimeout(() => {
      if (pendingRequests.has(requestId)) {
        pendingRequests.delete(requestId)
        reject(new Error(`Request to ${resource} timed out after ${5000} ms`))
      }
    }, 5000)

    // Save the promise hooks to the registry
    pendingRequests.set(requestId, { resolve, reject, timeoutId })

    const request = new Request(resource, options)

    request.blob().then((value) => {
      value.text().then((text) => {
        // Construct the serialized envelope
        const requestPayload = {
          id: requestId,
          type: 'request',
          path: URL.parse(request.url)?.pathname.replace('/api', ''),
          method: request.method,
          body: text,
        }

        // Send via WebRTC
        if (dataChannel.value) dataChannel.value.send(JSON.stringify(requestPayload))
      })
    })
  })
}

export function handleResponse(message: DcMessage) {
  assert(message.type == 'response')

  if (pendingRequests.has(message?.id)) {
    const { resolve, timeoutId } = pendingRequests.get(message.id)
    clearTimeout(timeoutId) // Stop the timeout clock
    pendingRequests.delete(message.id) // Clean up registry

    const response = new Response(JSON.stringify(message.body), {
      status: message.status,
      headers: { 'Content-Type': 'application/json' },
    })

    resolve(response)
  }
}
controllerClient.setConfig({
  baseUrl: window.location.origin + '/api',
  fetch: sendRequest,
})

siteManagerClient.setConfig({
  baseUrl: window.location.origin + '/api',
  auth: () => localStorage.getItem('auth_token') ?? '',
})

let activeRefreshPromise: Promise<string> | null = null

function handleLogout() {
  localStorage.removeItem('auth_token')

  if (router.currentRoute.value.name === 'Login') {
    return
  }

  ElNotification.error({ title: 'Session Expired', message: 'Please log in again.' })

  router.push({
    name: 'Login',
    query: { redirect: router.currentRoute.value.fullPath },
  })
}

async function authInterceptor(response: Response, request: Request) {
  if (request.url.includes('/token')) return response

  const status = response.status

  switch (status) {
    case 401:
      if (request.url.includes('/refresh')) {
        handleLogout()
        return response
      }
      // Handle unauthorized / token expired
      if (!activeRefreshPromise) {
        activeRefreshPromise = (async () => {
          try {
            const result = await refreshTokenAuthRefreshPost({
              client: siteManagerClient,
            })
            if (result.error || !result.data) {
              throw new Error('Refresh token invalid or expired')
            }

            const auth_token = result.data

            localStorage.setItem('auth_token', auth_token.access_token)

            return auth_token.access_token
          } catch (err) {
            handleLogout()
            throw err
          } finally {
            activeRefreshPromise = null
          }
        })()
      }

      try {
        const freshToken = await activeRefreshPromise

        const retriedRequest = request.clone()
        retriedRequest.headers.set('Authorization', `Bearer ${freshToken}`)

        return await fetch(retriedRequest)
      } catch {
        activeRefreshPromise = null
        return response
      }

    case 403:
      // Handle forbidden access
      ElNotification.error({
        title: 'Access Denied',
        message: 'You do not have permission to view this resource.',
      })
      break

    case 500:
      // Handle server crashes
      ElNotification.error({
        title: 'Server Error',
        message: 'Something went wrong on our end. Please try again later.',
      })
      break

    default:
      // Handle network errors or unhandled status codes
      if (!status) {
        ElNotification.error({
          title: 'Network Error',
          message: 'Please check your internet connection.',
        })
      } else if (!response.ok) {
        ElNotification.error({
          title: `Network Error (${status})`,
          message: 'Please check your internet connection.',
        })
      }
      break
  }

  return response
}

siteManagerClient.interceptors.response.use(authInterceptor)

export { controllerClient, siteManagerClient }
