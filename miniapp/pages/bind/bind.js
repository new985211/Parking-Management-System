const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    plate: "",
    phone: "",
    ownerName: "",
    binding: false,
    vehicle: null
  },

  onShow() {
    this.loadVehicle();
  },

  async loadVehicle() {
    try {
      const data = await api.getVehicle(app.globalData.openid);
      if (data.plate_number) {
        this.setData({
          vehicle: data,
          plate: data.plate_number,
          phone: data.phone || "",
          ownerName: data.owner_name || ""
        });
      }
    } catch (e) {
      // not bound yet
    }
  },

  onPlateInput(e) {
    this.setData({ plate: e.detail.value.toUpperCase() });
  },

  onPhoneInput(e) {
    this.setData({ phone: e.detail.value });
  },

  onNameInput(e) {
    this.setData({ ownerName: e.detail.value });
  },

  async doBind() {
    const plate = this.data.plate.trim();
    if (!plate) {
      wx.showToast({ title: "请输入车牌号", icon: "none" });
      return;
    }
    if (plate.length < 7) {
      wx.showToast({ title: "请输入完整车牌号", icon: "none" });
      return;
    }

    this.setData({ binding: true });
    try {
      const result = await api.bindPlate(plate, app.globalData.openid);
      if (result.success) {
        app.globalData.plateNumber = plate;
        wx.showToast({ title: "绑定成功", icon: "success" });
        setTimeout(() => wx.switchTab({ url: "/pages/index/index" }), 1500);
      } else {
        wx.showToast({ title: result.error || "绑定失败", icon: "none" });
      }
    } catch (e) {
      wx.showToast({ title: "绑定失败", icon: "none" });
    }
    this.setData({ binding: false });
  },

  async doUnbind() {
    wx.vibrateShort({ type: "medium" });
    wx.showModal({
      title: "确认解绑",
      content: "解绑后将无法查看停车记录和在线缴费",
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.bindPlate("", app.globalData.openid);
            app.globalData.plateNumber = "";
            this.setData({ vehicle: null, plate: "", phone: "", ownerName: "" });
            wx.showToast({ title: "已解绑", icon: "success" });
          } catch (e) {
            wx.showToast({ title: "解绑失败", icon: "none" });
          }
        }
      }
    });
  }
});

  onShareAppMessage() {
    return {
      title: "停车场智能管理系统",
      path: "/pages/bind/bind"
    };
  }
