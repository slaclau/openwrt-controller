<script setup lang="ts">
import versionData from './version.json'
import { info as sdkInfo } from './sdk/source.json' with { type: 'json' }
import { info as controllerSdkInfo } from 'openwrt-controller/src/sdk/source.json' with { type: 'json' }
</script>

<template>
    Frontend Version: {{ versionData.frontend_version }}
    <el-divider direction="vertical" />
    Controller Frontend Version: {{ versionData.controller_frontend_version }}
    <el-divider direction="vertical" />
    Sdk Version: {{ sdkInfo.version }}
    <el-divider direction="vertical" />
    Controller Sdk Version: {{ controllerSdkInfo.version }}
</template>
