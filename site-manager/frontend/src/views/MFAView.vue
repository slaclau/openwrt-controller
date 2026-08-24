<script setup lang="ts">
import router from '@/router';
import { reactive } from 'vue';


const form = reactive({
  totp: '',
})

const handleSubmit = async () => {

}

const handleCancel = async () => {
  localStorage.removeItem("auth_token")
  router.back()
}
</script>

<template>
  <div style="max-width: 320px; margin: 100px auto">
    <h1>Two-Factor Authentication</h1>
    Please enter the code from your authenticator app.
    <el-form label-position="top">
      <el-form-item>
        <el-input v-model="form.totp" placeholder="code" />
      </el-form-item>

      <div style="display: grid; gap: 8px">
        <span>
          <el-button type="primary" style="width: 100%" @click="handleSubmit"> Submit </el-button>
        </span>
        <span>
          <el-button style="width: 100%" @click="handleCancel"> Cancel </el-button>
        </span>
      </div>
    </el-form>
  </div>
</template>