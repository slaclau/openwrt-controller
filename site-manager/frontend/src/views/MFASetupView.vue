<script setup lang="ts">
import router from '@/router';
import { skipMfaAuthMfaSkipPost } from '@/sdk';
import { reactive } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute()

const form = reactive({
  totp: '',
})

const handleSubmit = async () => {

}

const handleSkip = async () => {
  const token = (await skipMfaAuthMfaSkipPost()).data?.access_token
  if (token) {
    localStorage.setItem("auth_token", token)
    const target = (route.query.redirect as string) || '/'
    router.push(target)
  }
}
</script>

<template>
  <div style="max-width: 320px; margin: 100px auto">
    <h1>Two-Factor Authentication</h1>
    Please scan the QR code to configure two factor authentication.
    Then enter the code from your authenticator app below.
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