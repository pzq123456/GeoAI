/**
 * GeoAI 前端服务封装
 */
export class GeoAIService {
  constructor(baseUrl = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  /**
   * 发送聊天请求并处理流式 SSE 响应
   * @param {Object} params 
   * @param {string} params.query 用户输入
   * @param {Array} params.history 历史记录
   * @param {Object} [params.context_features] 可选的地理上下文
   * @param {Object} handlers 回调处理函数
   */
  async chat({ query, history = [], context_features = null }, {
    onStatus,      // 过程状态回调
    onGeoJson,     // 地理数据回调
    onFinal,       // 最终报告回调
    onError        // 错误回调
  }) {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, history, context_features }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      // 处理 SSE 流
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        
        // SSE 格式通常是 "data: {...}\n\n"，这里进行解析
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const rawData = line.replace("data: ", "").trim();
            if (!rawData) continue;

            try {
              const parsed = JSON.parse(rawData);
              this._handleMessage(parsed, { onStatus, onGeoJson, onFinal });
            } catch (e) {
              console.error("解析 SSE 数据片段失败", e);
            }
          }
        }
      }
    } catch (err) {
      if (onError) onError(err);
      else console.error("GeoAI Service Error:", err);
    }
  }

  // 内部路由逻辑：分发不同类型的数据
  _handleMessage(message, { onStatus, onGeoJson, onFinal }) {
    const { type, data } = message;

    switch (type) {
      case "status":
        if (onStatus) onStatus(data);
        break;
      case "final_result":
        // 最终结果里包含 report, geojson, new_history
        if (data.geojson && onGeoJson) {
          onGeoJson(data.geojson);
        }
        if (onFinal) {
          onFinal({
            report: data.report,
            history: JSON.parse(data.new_history) // 后端传的是 JSON 字符串
          });
        }
        break;
      case "error":
        throw new Error(data);
      default:
        console.warn("未知消息类型:", type);
    }
  }
}

// 导出单例
export const geoAI = new GeoAIService();