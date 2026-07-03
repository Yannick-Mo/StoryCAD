export default function Footer() {
  return (
    <footer className="text-center py-6 mt-8 text-xs text-gray-600 border-t border-gray-800">
      <strong className="text-gray-500">StoryCAD</strong> — AI 写作辅助设计系统 · 让每一个灵感都变成坚实的长篇蓝图
      &nbsp;|&nbsp;
      <a href="/docs" className="text-blue-400 hover:underline no-underline">使用文档</a>
      &nbsp;·&nbsp;
      <a href="/changelog" className="text-blue-400 hover:underline no-underline">更新日志</a>
      &nbsp;·&nbsp;
      <a href="/feedback" className="text-blue-400 hover:underline no-underline">反馈建议</a>
    </footer>
  )
}
