const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    vehicle: null,
    currentParking: null,
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
        api.getVehicle(openid).catch(() => ({})),
        api.getCurrentParking(openid).catch(() => ({ current: null }))
      ]);
      this.setData({
        vehicle: vehicle.plate_number ? vehicle : null,
        currentParking: current.current || null,
        loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
      if (app.globalData.openid) {
        wx.showToast({ title: "加载失败，下拉刷新", icon: "none", duration: 2000 });
      }
    }
  },

  onPullDownRefresh() {
    this.loadData().then(() => wx.stopPullDownRefresh());
  }
});

  onShareAppMessage() {
    return {
      title: "停车场智能管理系统",
      path: "/pages/index/index"
    };
  }
