# 商品功能配置

商品面板使用 Rakuten Ichiba 官方 API：

- 商品热榜：Ichiba Item Ranking API，使用 `period=realtime`
- 商品搜索：Ichiba Item Search API

首次运行前，在 `product_config.json` 填入：

```json
{
  "applicationId": "你的 Application ID",
  "accessKey": "你的 Access Key",
  "affiliateId": "可留空",
  "hits": 20,
  "ranking_period": "realtime"
}
```

程序不会把密钥写入 Python 源码。
