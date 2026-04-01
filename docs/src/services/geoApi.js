/**
 * GeoAI 前端服务封装
 */
export class GeoAIService {
  constructor(baseUrl = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  async chat({ query, history = []}, {
    onStatus, onGeoJson, onFinal, onError
  }) {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, history }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = ""; // 【新增】用于处理跨 chunk 的数据缓冲

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // SSE 标准使用双换行符分隔消息
        const parts = buffer.split("\n\n");
        
        // 【关键】保留最后一个可能不完整的 part 到 buffer 中
        buffer = parts.pop();

        for (const part of parts) {
          const line = part.trim();
          if (line.startsWith("data: ")) {
            const rawData = line.replace("data: ", "").trim();
            if (!rawData) continue;

            try {
              let parsed = JSON.parse(rawData);
              if (typeof parsed === 'string') {
                parsed = JSON.parse(parsed);
              }
              this._handleMessage(parsed, { onStatus, onGeoJson, onFinal });
            } catch (e) {
              console.error("解析 SSE 数据失败。Raw:", rawData, "Error:", e);
            }
          }
        }
      }
    } catch (err) {
      if (onError) onError(err);
      else console.error("GeoAI Service Error:", err);
    }
  }

  _handleMessage(message, { onStatus, onGeoJson, onFinal }) {
    const { type, data } = message;

    switch (type) {
      case "status":
        if (onStatus) onStatus(data);
        break;
      case "final_result":
        if (data.geojson && onGeoJson) {
          onGeoJson(data.geojson);
        }
        if (onFinal) {
          onFinal({
            report: data.report,
            // 【修复】不要再对 data.new_history 进行 JSON.parse，它已经是对象了
            history: data.new_history 
          });
        }
        break;
      case "error":
        console.error("Agent 运行报错:", data);
        break;
      default:
        console.warn("未知消息类型:", type);
    }
  }
}

export const geoAI = new GeoAIService();