<script setup lang="ts">
import { onMounted, reactive, ref, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { site_manager_client } from '@/client'
import {
  getListOfOidcProvidersAuthProvidersGet,
  loginForAccessTokenAuthLoginPost,
  type OidcProvider,
} from '@/sdk'

const router = useRouter()
const route = useRoute()

const form = reactive({
  username: '',
  password: '',
})

const handleLogin = async () => {
  if (form.username && form.password) {
    const response = await loginForAccessTokenAuthLoginPost({
      client: site_manager_client,
      body: { username: form.username, password: form.password },
    })
    const token = response.data?.access_token
    if (!response.error && token) {
      localStorage.setItem('auth_token', token)
      ElNotification.success({ title: 'Logged In', message: 'You have successfully logged in.' })

      // Redirect back or to dashboard
      const target = (route.query.redirect as string) || '/'
      router.push(target)
    } else {
      ElMessage.error('Invalid credentials')
    }
  } else {
    ElMessage.error('Please fill in all fields')
  }
}

const handleRegister = () => {
  router.push({ path: "/register", query: { username: form.username } })
}


const auth_providers: Ref<OidcProvider[]> = ref([])

onMounted(async () => {
  if (route.params.provider) {
    window.location.href = window.location.origin + `/api/auth/${route.params.provider}/login`
  }
  const providers = (await getListOfOidcProvidersAuthProvidersGet({ client: site_manager_client }))
    .data
  if (providers) auth_providers.value = providers
})

const origin = window.location.origin
</script>

<template>
  <div style="max-width: 320px; margin: 100px auto">
    <h1>Login</h1>
    <el-form label-position="top">
      <el-form-item label="Username">
        <el-input v-model="form.username" placeholder="Username" />
      </el-form-item>

      <el-form-item label="Password">
        <el-input v-model="form.password" type="password" placeholder="Password" show-password />
      </el-form-item>

      <div style="display: grid; gap: 8px">
        <span>
          <el-button type="primary" style="width: 100%" @click="handleLogin"> Login </el-button>
        </span>
        <span>
          <el-button style="width: 100%" @click="handleRegister"> Register </el-button>
        </span>
      </div>
    </el-form>
    <el-divider v-if="auth_providers.length > 0" />
    <div style="display: grid; gap: 8px">
      <div v-for="provider in auth_providers" :key="provider.slug">
        <a :href="origin + `/api/auth/${provider.slug}/login`">
          <el-button style="width: 100%" class="custom-img-btn mb-4">
            <img v-if="provider.logo_url" :src="provider.logo_url" class="btn-left-img" />
            Login with {{ provider.name }}
          </el-button>
        </a>
      </div>
    </div>
  </div>
</template>

<style>
.custom-img-btn {
  position: relative;
  padding-left: 40px;
  padding-right: 40px;
  min-width: 180px;
}

.btn-left-img {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  object-fit: contain;
}
</style>
