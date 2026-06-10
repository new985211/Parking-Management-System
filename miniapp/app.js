App({
  globalData: {
    apiBase: "https://your-server.com",  // Change to your server URL
    openid: "",
    plateNumber: ""
  },

  onLaunch() {
    // Get WeChat openid via wx.login
    this.getOpenId();
  },

  getOpenId() {
    const app = this;
    wx.login({
      success(res) {
        if (res.code) {
          wx.request({
            url: `${app.globalData.apiBase}/api/miniapp/login`,
            method: "POST",
            data: { code: res.code },
            success(r) {
              if (r.data && r.data.openid) {
                app.globalData.openid = r.data.openid;
                app.loadVehicle();
              }
            }
          });
        }
      }
    });
  },

  loadVehicle() {
    const app = this;
    if (!app.globalData.openid) return;
    wx.request({
      url: `${app.globalData.apiBase}/api/miniapp/vehicle`,
      data: { openid: app.globalData.openid },
      success(r) {
        if (r.data && r.data.plate_number) {
          app.globalData.plateNumber = r.data.plate_number;
        }
      }
    });
  }
});
