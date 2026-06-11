const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    currentParking: null,
    paying: false,
    paid: false
  },

  onShow() {
    this.loadCurrent();
  },

  async loadCurrent() {
    try {
      const data = await api.getCurrentParking(app.globalData.openid);
      this.setData({ currentParking: data.current || null });
    } catch (e) {
      // no current parking
    }
  },

  async doPayment() {
    wx.vibrateShort({ type: "heavy" });
    if (!this.data.currentParking) return;
    this.setData({ paying: true });

    try {
      const result = await api.createPayment(
        this.data.currentParking.record_id,
        app.globalData.openid
      );

      if (result.success) {
        // Call WeChat Pay
        wx.requestPayment({
          timeStamp: result.timeStamp,
          nonceStr: result.nonceStr,
          package: result.package,
          signType: result.signType || "MD5",
          paySign: result.paySign,
          success: () => {
            this.setData({ paid: true, paying: false });
            wx.showToast({ title: "支付成功", icon: "success" });

            // Notify backend to open gate
            wx.request({
              url: `${app.globalData.apiBase}/api/gate/open`,
              method: "POST",
              data: { gate_id: "exit_gate" }
            });
          },
          fail: (err) => {
            this.setData({ paying: false });
            if (err.errMsg.indexOf("cancel") === -1) {
              wx.showToast({ title: "支付失败", icon: "error" });
            }
          }
        });
      } else {
        this.setData({ paying: false });
        wx.showToast({ title: result.error || "创建订单失败", icon: "none" });
      }
    } catch (e) {
      this.setData({ paying: false });
      wx.showToast({ title: "支付异常", icon: "none" });
    }
  }
});

  onShareAppMessage() {
    return {
      title: "停车场智能管理系统",
      path: "/pages/payment/payment"
    };
  }
