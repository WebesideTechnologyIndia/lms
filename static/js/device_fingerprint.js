// Device Fingerprinting - SHA256 based unique ID

class DeviceFingerprint {
    async getBrowserInfo() {
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            vendor: navigator.vendor || '',
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack || '',
        };
    }

    getScreenInfo() {
        return {
            width: screen.width,
            height: screen.height,
            colorDepth: screen.colorDepth,
            pixelDepth: screen.pixelDepth,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight,
        };
    }

    getTimezoneInfo() {
        return {
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            offset: new Date().getTimezoneOffset(),
        };
    }

    getHardwareInfo() {
        return {
            cpuCores: navigator.hardwareConcurrency || 0,
            deviceMemory: navigator.deviceMemory || 0,
            maxTouchPoints: navigator.maxTouchPoints || 0,
        };
    }

    getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = 200;
            canvas.height = 50;
            
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(10, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('Device ID 🔐', 2, 15);
            
            return canvas.toDataURL();
        } catch (e) {
            return 'canvas_error';
        }
    }

    getWebGLFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            if (!gl) return 'no_webgl';
            
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                return {
                    vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
                    renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL),
                };
            }
            return 'no_debug_info';
        } catch (e) {
            return 'webgl_error';
        }
    }

    async getDeviceData() {
        return {
            browser: await this.getBrowserInfo(),
            screen: this.getScreenInfo(),
            timezone: this.getTimezoneInfo(),
            hardware: this.getHardwareInfo(),
            canvas: this.getCanvasFingerprint(),
            webgl: this.getWebGLFingerprint(),
        };
    }

    async sha256(message) {
        const msgBuffer = new TextEncoder().encode(message);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async generateDeviceID() {
        const deviceData = await this.getDeviceData();
        const dataString = JSON.stringify(deviceData);
        const deviceID = await this.sha256(dataString);
        
        return {
            deviceID: deviceID,
            deviceName: this.getDeviceName(deviceData),
            rawData: deviceData
        };
    }

    getDeviceName(data) {
        const ua = data.browser.userAgent;
        let name = '';
        
        // OS Detection
        if (ua.includes('Windows')) name += 'Windows';
        else if (ua.includes('Mac')) name += 'Mac';
        else if (ua.includes('Linux')) name += 'Linux';
        else if (ua.includes('Android')) name += 'Android';
        else if (ua.includes('iPhone') || ua.includes('iOS')) name += 'iPhone';
        else name += 'Unknown OS';
        
        name += ' - ';
        
        // Browser Detection
        if (ua.includes('Chrome') && !ua.includes('Edg')) name += 'Chrome';
        else if (ua.includes('Safari') && !ua.includes('Chrome')) name += 'Safari';
        else if (ua.includes('Firefox')) name += 'Firefox';
        else if (ua.includes('Edg')) name += 'Edge';
        else name += 'Unknown Browser';
        
        return name;
    }

    async getOrCreateDeviceID() {
        let stored = localStorage.getItem('device_fingerprint');
        
        if (stored) {
            try {
                return JSON.parse(stored);
            } catch (e) {
                // Generate new if parse fails
            }
        }
        
        const fingerprint = await this.generateDeviceID();
        localStorage.setItem('device_fingerprint', JSON.stringify(fingerprint));
        return fingerprint;
    }
}

// Global instance
const deviceFingerprint = new DeviceFingerprint();