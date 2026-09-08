<script setup lang="ts">
import { onMounted, onUnmounted, ref, type Ref } from 'vue'

import type { AbstractDuplexConnection } from 'rpc-router/src/protocol'
import { DuplexRouter } from 'rpc-router/src/types'
import { WebsocketClient } from 'rpc-router/src/backends/websockets'

import { getIceServersIceServersGet } from '@/sdk'
import { getVersionVersionGet as getControllerVersionVersionGet } from 'openwrt-controller/src/sdk'
import { controllerClient, dataChannel, handleResponse, sendRequest, siteManagerClient } from '@/client.ts'
import { useRoute } from 'vue-router'


import TabBar from 'openwrt-controller/src/components/TabBar.vue'
import router from '@/router'
import { ElMessage } from 'element-plus'

const connected: Ref<boolean> = ref(false)
const route = useRoute()
let peerConnection: RTCPeerConnection
let connection: AbstractDuplexConnection

const rpc_router = new DuplexRouter()
const client = new WebsocketClient(rpc_router, window.origin + '/api/ws')

enum SiteConnectionState {
  Down = "DOWN",
  HttpConnected = "HTTP_CONNECTED",
  WsConnected = "WS_CONNECTED",
  WebRtcConnected = "WEBRTC_CONNECTED"
}

const state: Ref<SiteConnectionState | null> = ref(null)

rpc_router.on("webrtc_answer", async (payload) => {
  console.log("Received WebRTC answer", payload.answer)
  peerConnection.setRemoteDescription(payload.answer)
})

export interface DcMessage {
  type: 'response'
  id: string
  body: string
  status: number
}

async function connect(url: string) {
  connection = await client.connect()
  state.value = SiteConnectionState.WsConnected

  let res = await connection.call("initiate_webrtc", { site_id: route.params.site_id }).catch((err) => {
    console.error("failed to initiate webrtc:", err)
    router.back()
    ElMessage.error("Failed to negotiate WebRTC connection")
  })
  console.log("attempted to initiate webrtc:", res)

  const configuration = (await getIceServersIceServersGet()).data
  if (!configuration) return
  peerConnection = new RTCPeerConnection(configuration)
  const dc = peerConnection.createDataChannel('http')
  dataChannel.value = dc

  dc.addEventListener('open', async () => {
    console.log('dc open')

    const stats = await peerConnection.getStats()
    let activePair: RTCIceCandidatePairStats | null = null
    stats.forEach(report => {
      if (report.type === 'transport' && report.selectedCandidatePairId) {
        activePair = stats.get(report.selectedCandidatePairId) as RTCIceCandidatePairStats;
      } else if (report.type === 'candidate-pair' && report.state === 'succeeded' && report.nominated) {
        // Fallback for older spec implementations
        activePair = report as RTCIceCandidatePairStats;
      }
    });

    if (activePair !== null) {
      // Cast the looked up candidates to RTCIceCandidateStats
      const localCandidate = stats.get((activePair as any).localCandidateId);
      const remoteCandidate = stats.get((activePair as any).remoteCandidateId);

      if (!localCandidate || !remoteCandidate) {
        console.log("Found active pair but matching candidate stats are missing.");
        return;
      }

      if (localCandidate.candidateType === 'host' && remoteCandidate.candidateType === 'host') {
        console.log("Pure direct connection! No STUN or TURN servers used. Requesting local IP from Site");
        const localIp = (await connection.call("report_ips", { site_id: route.params.site_id })).local
        switch (localIp.version) {
          case 4:
            controllerClient.setConfig({ fetch: undefined, baseUrl: `http://${localIp}:5173/api` })
            break
          case 6:
            controllerClient.setConfig({ fetch: undefined, baseUrl: `http://[${localIp}]:5173/api` })
            break
        }

        console.log(controllerClient.getConfig())
        console.log("trying direct fetch")
      } else if (localCandidate.candidateType === 'srflx' || remoteCandidate.candidateType === 'srflx') {
        console.log("Direct connection established via STUN.");
      } else if (localCandidate.candidateType === 'relay' || remoteCandidate.candidateType === 'relay') {
        console.log("Connection is relayed through a TURN server.");
      }
    } else {
      console.log("No active connection pair found yet.");
    }

    if ((await getControllerVersionVersionGet()).error) {
      console.warn("Direct fetch faild")
      controllerClient.setConfig({
        baseUrl: window.location.origin + '/api',
        fetch: sendRequest,
      })
    }
    else {
      console.log("Direct fetch succeeded")
    }
    state.value = SiteConnectionState.WebRtcConnected
    connected.value = true
  })

  dc.addEventListener('message', (message) => {
    console.debug(`received ${message} from the remote site`)
    const data: DcMessage = JSON.parse(message.data)
    switch (data.type) {
      case 'response':
        handleResponse(data)
        break
      default:
        console.warn('unexpected data channel message', data)
    }
  })

  peerConnection.addEventListener('icecandidate', async (event) => {
    await connection.send("add_ice_candidate", { candidate: event.candidate, site_id: route.params.site_id })
    console.debug('Gathered new ICE candidate and sent to site manager', event.candidate)
  })

  peerConnection.addEventListener('icegatheringstatechange', () => {
    console.log('ICE Gathering state is', peerConnection.iceGatheringState)
  })

  peerConnection.createOffer().then(async (offer) => {
    peerConnection.setLocalDescription(offer)
    let res = await connection.call("webrtc_offer", { offer, site_id: route.params.site_id }, 5000)
    console.debug('Created WebRTC offer and sent to site manager, received answer', offer, res)
  })
}

onMounted(async () => {
  console.log('site view mounted for', route.params.site_id)
  await connect(window.origin + '/api/ws')
})

onUnmounted(async () => {
  await connection.close()
  if (peerConnection) peerConnection.close()
})
</script>

<template>
  <!-- {{ state }} -->
  <div v-loading="!connected">
    <div style="padding-bottom: 86px">
      <router-view v-if="connected" />
    </div>
    <TabBar style="margin-bottom: 59px" />
  </div>
</template>
