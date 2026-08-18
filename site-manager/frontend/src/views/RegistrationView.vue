<script setup lang="ts">
import { site_manager_client } from '@/client';
import router from '@/router';
import { registerUserUsersRegisterPost } from '@/sdk';
import { ElMessage, ElNotification } from 'element-plus';
import { onMounted, reactive } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

onMounted(() => {
  // Safely pre-populate the email
  if (route.query.username) {
    form.username = route.query.username.toString()
  }
})

const form = reactive({
  full_name: '',
  email: '',
  username: '',
  password: '',
})

const handleRegister = async () => {
  if (form.full_name && form.email && form.username && form.password) {
    const response = await registerUserUsersRegisterPost({
      client: site_manager_client,
      body: { full_name: form.full_name, email: form.email, username: form.username, password: form.password },
    })
    if (!response.error) {
      ElNotification.success({ title: 'Registered', message: 'You have successfully registered. Please log in.' })

      // Redirect back or to dashboard
      router.back()
    } else {
      ElMessage.error('Failed to create an account')
    }
  } else {
    ElMessage.error('Please fill in all fields')
  }
}
</script>

<template>
  <div style="max-width: 320px; margin: 100px auto">
    <h1>Register</h1>
    <el-form label-position="top">
      <el-form-item label="Full Name">
        <el-input v-model="form.full_name" placeholder="Full Name" />
      </el-form-item>

      <el-form-item label="Email Address">
        <el-input v-model="form.email" placeholder="Email Address" />
      </el-form-item>

      <el-form-item label="Username">
        <el-input v-model="form.username" placeholder="Username" />
      </el-form-item>

      <el-form-item label="Password">
        <el-input v-model="form.password" type="password" placeholder="Password" show-password />
      </el-form-item>

      <span>
        <el-button style="width: 100%" @click="handleRegister"> Register </el-button>
      </span>
    </el-form>
  </div>
</template>