import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'cn.qijianqiannian.app',
  appName: '器见千年',
  webDir: 'dist',
  server: {
    androidScheme: 'http',
  },
  android: {
    allowMixedContent: true,
  },
}

export default config
