<script setup lang="ts">
import router from '@/router'
import {
  exchangeCodeForTokenAndLinkAccountAuthOidcLinkAccountPost,
  getListOfOidcProvidersAuthOidcProvidersGet,
  type OidcProvider,
} from '@/sdk'
import { ElMessage, ElNotification } from 'element-plus'
import { onMounted, reactive, ref, type Ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const form = reactive({
  username: '',
  password: '',
})

const pending = ref('')

const handleLink = async () => {
  if (form.username && form.password) {
    const response = await exchangeCodeForTokenAndLinkAccountAuthOidcLinkAccountPost({
      body: {
        username: form.username,
        password: form.password,
        code: pending.value,
      },
    })
    const token = response.data?.access_token
    if (!response.error && token) {
      localStorage.setItem('auth_token', token)
      ElNotification.success({
        title: 'Account Linked',
        message: 'You have successfully linked your account.',
      })

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

const auth_providers: Ref<OidcProvider[]> = ref([])

onMounted(async () => {
  if (route.query.pending) pending.value = route.query.pending.toString()

  router.push(route.path)
  const providers = (await getListOfOidcProvidersAuthOidcProvidersGet()).data
  if (providers) auth_providers.value = providers
})

const origin = window.location.origin
</script>

<template>
  <div style="max-width: 320px; margin: 100px auto">
    <h1>Link Account</h1>
    There is an existing account with this email address, please enter your credentials to authorize
    the link or login with an external account with which you have linked previously.
    <el-form label-position="top">
      <el-form-item label="Username">
        <el-input v-model="form.username" placeholder="Username" />
      </el-form-item>

      <el-form-item label="Password">
        <el-input v-model="form.password" type="password" placeholder="Password" />
      </el-form-item>

      <el-button type="primary" style="width: 100%" @click="handleLink"> Link Account </el-button>
    </el-form>
    <el-divider />
    <div style="display: grid; gap: 8px">
      <div v-for="provider in auth_providers" :key="provider.slug">
        <a :href="origin + `/api/auth/${provider.slug}/login?pending=${pending}`">
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
