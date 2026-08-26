<script setup lang="ts">
import SvgIcon from '@jamescoyle/vue-icon'

import { ElDrawer } from 'element-plus'

import {
  getListOfOidcProvidersAuthOidcProvidersGet,
  readUsersMeAuthInfoGet,
  type OidcProvider,
  type UserFullPublic,
  delinkAccountAuthProviderDelinkPost,
  updateUsersMePost,
  type UpdateUserData,
  deleteMfaAuthMfaIdDelete,
  beginRegistrationAuthPasskeysRegisterBeginPost,
} from '@/sdk'
import { mdiAccount } from '@mdi/js'
import { computed, onMounted, reactive, ref, watch, type Ref } from 'vue'
import { logout } from '@/utils'
import router from '@/router'
import { useRoute } from 'vue-router'

const route = useRoute()

const user: Ref<UserFullPublic | null> = ref(null)

const userUpdate: UpdateUserData = reactive({
  username: '',
  full_name: '',
  display_name: ''
})
const initialUserUpdate = ref({ ...userUpdate })
const activeAuthProviders: Ref<string[]> = ref([])

const auth_providers: Ref<OidcProvider[]> = ref([])


const onOpen = async () => {
  const response = await readUsersMeAuthInfoGet()
  if (response.data) user.value = response.data
  if (user.value?.remote_users)
    activeAuthProviders.value = user.value.remote_users.flatMap((remoteUser) => remoteUser.provider)
  userUpdate.username = user.value?.username ?? ''
  userUpdate.full_name = user.value?.full_name ?? ''
  userUpdate.display_name = user.value?.display_name ?? ''
  initialUserUpdate.value = { ...userUpdate }
}


const changed = computed(() => {
  return JSON.stringify(initialUserUpdate.value) !== JSON.stringify(userUpdate)
})


onMounted(async () => {
  const providers = (await getListOfOidcProvidersAuthOidcProvidersGet()).data
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

const handleUpdateInformation = async () => {
  const res = await updateUsersMePost({ body: userUpdate })
  if (res.data) user.value = res.data
  initialUserUpdate.value = { ...userUpdate }
}

const addMfaConfiguration = () => {
  router.push({
    name: 'SetupMFA', query: {
      skip: 'disabled',
      redirect: route.fullPath
    }
  })
  drawerRef.value?.handleClose()
}

const removeMfaConfiguration = async (id: string) => {
  const res = await deleteMfaAuthMfaIdDelete({ path: { id } })
  if (!res.error) await onOpen()
}

const addPasskey = async () => {
  let credential = await navigator.credentials.create()
  console.log(credential)
  const res = await beginRegistrationAuthPasskeysRegisterBeginPost()
}

</script>

<template>
  <el-drawer destroy-on-close @open="onOpen" ref="drawerRef">
    <template #header>
      <span>
        <svg-icon style="float: left" type="mdi" :path="mdiAccount" :size="24" />
        {{ user?.display_name || user?.full_name }}
      </span>
      <el-button @click="handleLogout" :disabled="!$route.meta.requiresAuth"> Logout </el-button>
    </template>
    <!-- {{ user }} -->

    <el-divider>User Information</el-divider>
    <el-form label-position="right" label-width="auto">
      <el-form-item label="Full Name">
        <el-input v-model="userUpdate.full_name" />
      </el-form-item>
      <el-form-item label="Display Name">
        <el-input v-model="userUpdate.display_name" />
      </el-form-item>
      <el-form-item label="Username">
        <el-input :disabled="true" v-model="userUpdate.username" />
      </el-form-item>
      <span>
        <el-button style="width: 100%" type="primary" :disabled="!changed" @click="handleUpdateInformation"> Save
        </el-button>
      </span>
    </el-form>

    <el-divider> Remote Login Providers </el-divider>
    <el-button v-for="provider in auth_providers" :key="provider" style="width: 100%" class="custom-img-btn mb-4"
      @click="() => onClickRemoteProvider(provider.slug)">
      <img v-if="provider.logo_url" :src="provider.logo_url" class="btn-left-img" />
      {{ activeAuthProviders.includes(provider.slug) ? 'Deauthorize' : 'Authorize' }}
      {{ provider.name }}
    </el-button>

    <el-divider>MFA Configurations</el-divider>
    <el-form label-width="auto" label-position="left">
      <el-form-item v-for="config in user?.active_totp_configurations"
        :label="`${config.device_name} created on ${new Date(Date.parse(config.created_at)).toLocaleDateString()}`">
        <el-button style="width: 100%" @click="removeMfaConfiguration(config.id)">Remove</el-button>
      </el-form-item>
    </el-form>
    <el-button style="width: 100%" type="primary" @click="addMfaConfiguration">Add additional configuration</el-button>
    <el-divider>Passkeys</el-divider>
    <el-form label-width="auto" label-position="left">
      <!-- <el-form-item v-for="config in user?.active_totp_configurations"
        :label="`${config.device_name} created on ${new Date(Date.parse(config.created_at)).toLocaleDateString()}`">
        <el-button style="width: 100%" @click="removeMfaConfiguration(config.id)">Remove</el-button>
      </el-form-item> -->
    </el-form>
    <el-button style="width: 100%" type="primary" @click="addPasskey">Add a passkey</el-button>
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
