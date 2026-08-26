<script setup lang="ts">
import router from '@/router';
import { skipMfaAuthMfaSkipPost, setupMfaAuthMfaSetupGet, registerMfaAuthMfaRegisterPost } from '@/sdk';
import { reactive, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';

import QrcodeVue from 'qrcode.vue'
import { ElNotification } from 'element-plus';

const route = useRoute()

const form = reactive({
  totp: '',
})

const handleSubmit = async () => {
  const res = await registerMfaAuthMfaRegisterPost({ body: { code: form.totp } })
  if (res.data?.access_token) {
    localStorage.setItem("auth_token", res.data.access_token)

    ElNotification.success({ title: 'Logged In', message: 'You have successfully configured MFA.' })
    const target = (route.query.redirect as string) || '/'
    router.push(target)
  }
}

const handleSkip = async () => {
  const token = (await skipMfaAuthMfaSkipPost()).data?.access_token
  if (token) {
    localStorage.setItem("auth_token", token)

    ElNotification.success({ title: 'Logged In', message: 'You have skipped setting up MFA, you will be prompted to do so on your next login.' })
    const target = (route.query.redirect as string) || '/'
    router.push(target)
  }
}

const totp_url = ref("")

onMounted(async () => {
  const res = await setupMfaAuthMfaSetupGet()
  if (res.data?.url)
    totp_url.value = res.data?.url;
})

</script>

<template>
  <div style="max-width: 320px; margin: 100px auto">
    <h1>Two-Factor Authentication</h1>
    <div>
      Please scan the QR code or click <a :href="totp_url">here</a> to configure two factor authentication.
      Then enter the code from your authenticator app below.
    </div>
    <qrcode-vue :value="totp_url" />
    <el-form label-position="top">
      <el-form-item>
        <el-input v-model="form.totp" placeholder="code" />
      </el-form-item>

      <div style="display: grid; gap: 8px">
        <span>
          <el-button type="primary" style="width: 100%" @click="handleSubmit"> Submit </el-button>
        </span>
        <span>
          <el-button style="width: 100%" @click="handleSkip"> Skip </el-button>
        </span>
      </div>
    </el-form>
  </div>
</template>
