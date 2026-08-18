<script setup lang="ts">
import SvgIcon from '@jamescoyle/vue-icon'

import { site_manager_client } from '@/client';
import { getListOfOidcProvidersAuthProvidersGet, readUsersMeAuthInfoGet, type OidcProvider, type UserWithRemoteUsers, delinkAccountAuthProviderDelinkPost } from '@/sdk';
import { mdiAccount } from '@mdi/js';
import { onMounted, ref, type Ref } from 'vue';
import router from '@/router';
import { logout } from '@/utils';


const user: Ref<UserWithRemoteUsers | null> = ref(null);
const activeAuthProviders: Ref<string[]> = ref([])

const onOpen = async () => {
  const response = await readUsersMeAuthInfoGet({ client: site_manager_client })
  if (response.data)
    user.value = response.data
  if (user.value?.remote_users)
    activeAuthProviders.value = user.value.remote_users.flatMap((remoteUser) => remoteUser.provider)
}

const auth_providers: Ref<OidcProvider[]> = ref([])

onMounted(async () => {
  const providers = (await getListOfOidcProvidersAuthProvidersGet({ client: site_manager_client }))
    .data
  if (providers) auth_providers.value = providers
})

const origin = window.location.origin

const onClickRemoteProvider = async (provider: string) => {
  if (activeAuthProviders.value.includes(provider)) {
    const response = await delinkAccountAuthProviderDelinkPost({ client: site_manager_client, path: { provider } })
    if (!response.error)
      await onOpen()
  } else {
    window.location.href = origin + `/api/auth/${provider}/login`
  }
}
</script>

<template>
  <el-drawer destroy-on-close @open="onOpen">
    <template #header>
      <span>
        <svg-icon style="float: left" type="mdi" :path="mdiAccount" :size="24" />
        {{ user?.full_name }}
      </span>
      <el-button @click="logout" :disabled="!$route.meta.requiresAuth">
        Logout
      </el-button>
    </template>
    <!-- {{ user }} -->

    <el-divider> Remote Login Providers </el-divider>
    <el-button v-for="provider in auth_providers" style="width: 100%" class="custom-img-btn mb-4"
      @click="() => onClickRemoteProvider(provider.slug)">
      <img v-if="provider.logo_url" :src="provider.logo_url" class="btn-left-img" />
      {{ activeAuthProviders.includes(provider.slug) ?
        'Deauthorize' : 'Authorize'
      }}
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