<script setup lang="ts">
import SvgIcon from '@jamescoyle/vue-icon'

import { ElDrawer } from 'element-plus'

import {
  getListOfOidcProvidersAuthProvidersGet,
  readUsersMeAuthInfoGet,
  type OidcProvider,
  type UserWithRemoteUsers,
  delinkAccountAuthProviderDelinkPost,
} from '@/sdk'
import { mdiAccount } from '@mdi/js'
import { onMounted, ref, type Ref } from 'vue'
import router from '@/router'
import { logout } from '@/utils'

const user: Ref<UserWithRemoteUsers | null> = ref(null)
const activeAuthProviders: Ref<string[]> = ref([])

const onOpen = async () => {
  const response = await readUsersMeAuthInfoGet()
  if (response.data) user.value = response.data
  if (user.value?.remote_users)
    activeAuthProviders.value = user.value.remote_users.flatMap((remoteUser) => remoteUser.provider)
}

const auth_providers: Ref<OidcProvider[]> = ref([])

onMounted(async () => {
  const providers = (await getListOfOidcProvidersAuthProvidersGet()).data
  if (providers) auth_providers.value = providers
})

const origin = window.location.origin

const onClickRemoteProvider = async (provider: string) => {
  if (activeAuthProviders.value.includes(provider)) {
    const response = await delinkAccountAuthProviderDelinkPost({ path: { provider } })
    if (!response.error) await onOpen()
  } else {
    window.location.href = origin + `/api/auth/${provider}/login`
  }
}

const drawerRef: Ref<null | typeof ElDrawer> = ref(null)

const handleLogout = async () => {
  drawerRef.value?.handleClose()
  await logout()
}
</script>

<template>
  <el-drawer destroy-on-close @open="onOpen" ref="drawerRef">
    <template #header>
      <span>
        <svg-icon style="float: left" type="mdi" :path="mdiAccount" :size="24" />
        {{ user?.full_name }}
      </span>
      <el-button @click="handleLogout" :disabled="!$route.meta.requiresAuth"> Logout </el-button>
    </template>
    <!-- {{ user }} -->

    <el-divider> Remote Login Providers </el-divider>
    <el-button
      v-for="provider in auth_providers"
      style="width: 100%"
      class="custom-img-btn mb-4"
      @click="() => onClickRemoteProvider(provider.slug)"
    >
      <img v-if="provider.logo_url" :src="provider.logo_url" class="btn-left-img" />
      {{ activeAuthProviders.includes(provider.slug) ? 'Deauthorize' : 'Authorize' }}
      {{ provider.name }}
    </el-button>
  </el-drawer>
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
