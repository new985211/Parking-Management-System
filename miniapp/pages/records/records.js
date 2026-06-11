const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    records: [],
    page: 1,
    hasMore: true,
    loading: false
  },

  onShow() {
    this.setData({ records: [], page: 1, hasMore: true });
    this.loadRecords();
  },

  async loadRecords() {
    if (this.data.loading || !this.data.hasMore) return;
    this.setData({ loading: true });

    try {
      const data = await api.getRecords(app.globalData.openid, this.data.page);
      const records = data.records || [];
      this.setData({
        records: this.data.records.concat(records),
        page: this.data.page + 1,
        hasMore: records.length >= 20,
        loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    this.loadRecords();
  },

  onPullDownRefresh() {
    this.setData({ records: [], page: 1, hasMore: true });
    this.loadRecords().then(() => wx.stopPullDownRefresh());
  }
});

  onShareAppMessage() {
    return {
      title: "停车场智能管理系统",
      path: "/pages/records/records"
    };
  }
