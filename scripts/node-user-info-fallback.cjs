// 部分 Windows/Node 24 组合会让 os.userInfo() 抛出 ENOMEM，Capacitor 只用它读取 shell。
// 仅在系统调用失败时提供等价的环境变量兜底，不影响正常环境。
const os = require('node:os')

try {
  os.userInfo()
} catch {
  os.userInfo = () => ({
    uid: -1,
    gid: -1,
    username: process.env.USERNAME || 'user',
    homedir: process.env.USERPROFILE || process.cwd(),
    shell: process.env.ComSpec || 'cmd.exe',
  })
}
