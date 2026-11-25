import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../stores/Platform";
export default function AuthPage() {
  const { user, authenticate, logout } = useAuth(),
    navigate = useNavigate(),
    [params] = useSearchParams();
  const [register, setRegister] = useState(false),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="mx-auto w-full max-w-lg px-4 py-8 sm:px-6 sm:py-16">
      <h1 className="font-display text-3xl">
        {user ? "账号" : register ? "创建账号" : "登录"}
      </h1>
      {user ? (
        <div className="panel mt-6 p-4 sm:mt-8 sm:p-6">
          <p>{user.username}</p>
          <Link to="/learning" className="btn-gold mt-5">
            进入学习中心
          </Link>
          <button
            className="btn-ghost ml-3"
            onClick={() => logout().catch((e) => setError(e.message))}
          >
            退出登录
          </button>
        </div>
      ) : (
        <form
          className="panel mt-6 space-y-5 p-4 sm:mt-8 sm:p-6"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              await authenticate(register, username, password);
              const next = params.get("next");
              navigate(
                next?.startsWith("/") && !next.startsWith("//")
                  ? next
                  : "/learning",
              );
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label className="block text-sm">
            用户名
            <input
              required
              minLength={2}
              maxLength={40}
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="field mt-2"
            />
          </label>
          <label className="block text-sm">
            密码
            <input
              type="password"
              required
              minLength={8}
              maxLength={128}
              autoComplete={register ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field mt-2"
            />
            <span className="mt-1 block text-xs text-ink-soft">
              至少8个字符
            </span>
          </label>
          <button disabled={busy} className="btn-gold w-full sm:w-auto">
            {busy ? "提交中…" : register ? "注册并登录" : "登录"}
          </button>
          <button
            type="button"
            className="btn-ghost mt-3 w-full sm:ml-3 sm:mt-0 sm:w-auto"
            onClick={() => {
              setRegister(!register);
              setError("");
            }}
          >
            {register ? "已有账号" : "创建账号"}
          </button>
        </form>
      )}
      {error && (
        <p role="alert" className="mt-4 text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
