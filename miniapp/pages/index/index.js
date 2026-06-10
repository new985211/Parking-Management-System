const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    vehicle: null,
    currentParking: null,
    stats: { today_count: 0, total_fee: 0 },
    loading: true
  },

  onShow() {
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    const openid = app.globalData.openid;
    try {
      const [vehicle, current] = await Promise.all([
        api.getVehicle(openid),
        api.getCurrentParking(openid)
      ]);
      this.setData({
        vehicle: vehicle.plate_number ? vehicle : null,
        currentParking: current.current || null,
        loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
      wx.showToast({ title: "加载失败", icon: "none" });
    }
  },

  onPullDownRefresh() {
    this.loadData().then(() => wx.stopPullDownRefresh());
  }
});
