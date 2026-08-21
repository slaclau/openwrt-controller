import { ElNotification } from 'element-plus'
import { logoutAuthLogoutPost } from './sdk'
import router from './router'

export const logout = async () => {
  const logoutUrl = (await logoutAuthLogoutPost()).data?.location
  localStorage.removeItem('auth_token')
  console.log('logged out')
  ElNotification.success({
    title: 'Logged Out',
    message: 'You have been successfully logged out.',
  })
  if (logoutUrl) {
    window.location.href = logoutUrl
  } else {
    router.push({
      name: 'Login',
      query: { redirect: '/' },
    })
  }
}
