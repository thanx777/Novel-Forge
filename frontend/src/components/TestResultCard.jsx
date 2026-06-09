export default function TestResultCard({ result, onRetry }) {
  if (!result) return null
  const isSuccess = result.success
  const hintLabels = {
    timeout: '请求超时',
    invalid_api_key: 'API Key 无效',
    forbidden: '访问被拒绝',
    model_not_found: '模型不存在',
    rate_limit: '频率限制/配额不足',
    network_error: '网络连接失败',
    ssl_error: 'SSL 证书错误',
    empty_response: '模型返回为空',
    insufficient_balance: '余额不足',
    unknown: '未知错误',
    no_api_key: '未配置 API Key',
    no_base_url: '未配置 Base URL',
    no_model: '未配置模型',
  }

  return (
    <div className={`test-result-card ${isSuccess ? 'test-result-success' : 'test-result-fail'}`}>
      <div className="test-result-status">
        {isSuccess ? '✅ 连接成功' : `❌ ${hintLabels[result.hint] || result.hint || '连接失败'}`}
      </div>
      {result.model && (
        <div className="test-result-row">
          <span className="test-result-label">模型</span>
          <span className="test-result-value">{result.model}</span>
        </div>
      )}
      {result.elapsed_ms > 0 && (
        <div className="test-result-row">
          <span className="test-result-label">延迟</span>
          <span className="test-result-value">{result.elapsed_ms}ms{result.attempts ? ` (${result.attempts}次尝试)` : ''}</span>
        </div>
      )}
      {result.response && (
        <div className="test-result-row">
          <span className="test-result-label">响应</span>
          <span className="test-result-value test-result-response">{result.response}</span>
        </div>
      )}
      {!isSuccess && result.suggestion && (
        <div className="test-result-row">
          <span className="test-result-label">建议</span>
          <span className="test-result-value">{result.suggestion}</span>
        </div>
      )}
      {!isSuccess && result.error_detail && (
        <details className="test-result-error-detail">
          <summary>错误详情</summary>
          <code>{result.error_detail}</code>
        </details>
      )}
      {!isSuccess && onRetry && (
        <button className="test-result-retry-btn" onClick={onRetry}>重试</button>
      )}
    </div>
  )
}
