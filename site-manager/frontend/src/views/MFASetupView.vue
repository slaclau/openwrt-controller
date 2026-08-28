<script setup lang="ts">
import router from '@/router'
import {
  skipMfaAuthMfaSkipPost,
  setupMfaAuthMfaSetupGet,
  registerMfaAuthMfaRegisterPost,
} from '@/sdk'
import { reactive, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import QrcodeVue from 'qrcode.vue'
import { ElMessage, ElNotification } from 'element-plus'

const route = useRoute()

const form = reactive({
  device_name: 'Authenticator',
  totp: '',
})

const handleSubmit = async () => {
  const res = await registerMfaAuthMfaRegisterPost({
    body: { device_name: form.device_name, code: form.totp },
  })
  if (res.data?.access_token) {
    localStorage.setItem('auth_token', res.data.access_token)

    ElNotification.success({ title: 'Logged In', message: 'You have successfully configured MFA.' })
    const target = (route.query.redirect as string) || '/'
    router.push(target)
  } else ElMessage.error({ message: 'Invalid code. Please try again.' })
}

const handleSkip = async () => {
  const token = (await skipMfaAuthMfaSkipPost()).data?.access_token
  if (token) {
    localStorage.setItem('auth_token', token)

    ElNotification.success({
      title: 'Logged In',
      message: 'You have skipped setting up MFA, you will be prompted to do so on your next login.',
    })
    const target = (route.query.redirect as string) || '/'
    router.push(target)
  }
}

const totp_url = ref('')

onMounted(async () => {
  const res = await setupMfaAuthMfaSetupGet()
  if (res.data?.url) totp_url.value = res.data?.url
})
</script>

<template>
  <div style="max-width: 320px; margin: 20px auto">
    <h1>Two-Factor Authentication</h1>
    <div>
      Please scan the QR code or click <a :href="totp_url">here</a> to configure two factor
      authentication. Then enter the code from your authenticator app below.
    </div>
    <el-card :body-style="{ display: 'flex', justifyContent: 'center' }">
      <qrcode-vue :value="totp_url" :size="200" />
    </el-card>
    <el-form label-position="top">
      <el-form-item>
        <el-input v-model="form.device_name" placeholder="Device Name" />
      </el-form-item>
      <el-form-item>
        <el-input v-model="form.totp" placeholder="Code" />
      </el-form-item>

      <div style="display: grid; gap: 8px">
        <span>
          <el-button type="primary" style="width: 100%" @click="handleSubmit"> Submit </el-button>
        </span>
        <span>
          <el-button
            style="width: 100%"
            v-if="!($route.query.skip == 'disabled')"
            @click="handleSkip"
          >
            Skip
          </el-button>
        </span>
        <span>
          <el-button
            style="width: 100%"
            v-if="$route.query.skip == 'disabled'"
            @click="$router.back()"
          >
            Cancel
          </el-button>
        </span>
      </div>
    </el-form>
  </div>
</template>
