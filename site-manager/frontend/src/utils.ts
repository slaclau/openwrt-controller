import { ElNotification } from "element-plus"
import { site_manager_client } from "./client"
import { logoutAuthLogoutPost } from "./sdk"
import router from "./router"

export const logout = async () => {
    const logoutUrl = (
        await logoutAuthLogoutPost({ client: site_manager_client })
    ).data?.location
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