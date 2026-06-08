# 金吾财经港股IPO API 文档

Base URL: `https://ipo.jinwucj.com/api`
所有接口 POST 请求，Content-Type: `application/json`

## IPO 列表类接口

| 端点 | 功能 | 请求参数 |
|------|------|----------|
| `/makeNew/makeNewList` | 最新认购中 | `{}` |
| `/makeNew/getToBeListedList` | 待上市 | `{}` |
| `/makeNew/listedV` | 最新上市 | `{}` |
| `/makeNew/getTableDataByStatus` | 已递表 | `{"status":0/1, "pageNum":1, "pageSize":5}` |

## 招股详情类接口 (需传 stock code)

| 端点 | 功能 | 请求参数 |
|------|------|----------|
| `/offeringDetails/getOfferingDetails` | 招股详情 | `{"code":"02723.hk"}` |
| `/offeringDetails/getMarginInfo` | 融资认购动态 | `{"code":"02723.hk"}` |
| `/offeringDetails/getBrokerInfo` | 券商融资认购 | `{"code":"02723.hk"}` |
| `/offeringDetails/getCompanyProfile` | 公司概况 | `{"code":"06872.hk"}` |

## 配售结果类接口

| 端点 | 功能 | 请求参数 |
|------|------|----------|
| `/offeringDetails/getCompanyInfoByCode` | 配售结果-基本信息 | `{"code":"06872.hk"}` |
| `/offeringDetails/getOtherInfoByCode` | 配售结果-其他信息 | `{"code":"06872.hk"}` |
| `/offeringDetails/getPublicOfferingByCode` | 配售结果-中签分布 | `{"code":"00100.hk"}` |
