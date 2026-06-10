/**
 * Backend API wrapper for WeChat mini-program.
 * All API calls go through here.
 */
const app = getApp();

function request(path, method = "GET", data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + path,
      method: method,
      data: data,
      header: { "Content-Type": "application/json" },
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(res.data);
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

module.exports = {
  // Vehicle
  getVehicle(openid) {
    return request("/api/miniapp/vehicle?openid=" + openid);
  },

  bindPlate(plate, openid) {
    return request("/api/miniapp/bind", "POST", { plate_number: plate, openid: openid });
  },

  // Records
  getRecords(openid, page = 1) {
    return request("/api/miniapp/records?openid=" + openid + "&page=" + page);
  },

  getCurrentParking(openid) {
    return request("/api/miniapp/current?openid=" + openid);
  },

  // Payment
  createPayment(recordId, openid) {
    return request("/api/payment/create", "POST", { record_id: recordId, openid: openid });
  },

  getPaymentStatus(recordId) {
    return request("/api/payment/status?record_id=" + recordId);
  },

  // Stats
  getStats(openid) {
    return request("/api/miniapp/stats?openid=" + openid);
  }
};
