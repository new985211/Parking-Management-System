App({
  globalData: {
    apiBase: "https://your-server.com",
    openid: "",
    plateNumber: "",
    pendingCount: 0
  },

  onLaunch() {
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
                app.updateTabBarBadge();
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
  },

  updateTabBarBadge() {
    const app = this;
    wx.request({
      url: `${app.globalData.apiBase}/api/miniapp/current`,
      data: { openid: app.globalData.openid },
      success(r) {
        const current = r.data && r.data.current;
        if (current && current.fee > 0) {
          wx.setTabBarBadge({ index: 2, text: "¥" });
        } else {
          wx.removeTabBarBadge({ index: 2 });
        }
      }
    });
  }
});
