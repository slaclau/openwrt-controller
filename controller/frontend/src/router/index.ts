import { createRouter, createWebHistory } from 'vue-router'

export const routes = [
  {
    name: 'Overview',
    path: 'overview',
    component: () => import('@controller/views/OverviewView.vue'),
    alias: [''],
  },
  {
    name: 'Devices',
    path: 'devices',
    component: () => import('@controller/views/DevicesView.vue'),
  },
  {
    name: 'Clients',
    path: 'clients',
    //    component: () => import('@controller/views/ClientsView.vue'),
  },
  {
    name: 'DPI',
    path: 'dpi',
    component: () => import('@controller/views/DPIView.vue'),
  },
  {
    name: 'Settings',
    path: 'settings',
    component: () => import('@controller/views/SettingsView.vue'),
    children: [
      {
        name: 'Networks',
        path: 'network',
        component: () => import('@controller/views/NetworksView.vue'),
      },
      {
        name: 'WiFi',
        path: 'wifi',
        component: () => import('@controller/views/WirelessView.vue'),
      },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', children: routes }],
})
