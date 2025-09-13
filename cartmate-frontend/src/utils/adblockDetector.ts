// Ad blocker detection utility
export class AdBlockDetector {
  private static instance: AdBlockDetector;
  private isAdBlocked: boolean = false;
  private callbacks: Array<(blocked: boolean) => void> = [];

  private constructor() {
    this.detectAdBlock();
  }

  public static getInstance(): AdBlockDetector {
    if (!AdBlockDetector.instance) {
      AdBlockDetector.instance = new AdBlockDetector();
    }
    return AdBlockDetector.instance;
  }

  private detectAdBlock(): void {
    // Method 1: Try to create a fake ad element
    const fakeAd = document.createElement('div');
    fakeAd.innerHTML = '&nbsp;';
    fakeAd.className = 'adsbox';
    fakeAd.style.cssText = 'position:absolute;left:-10000px;top:-1000px;width:1px;height:1px;';
    
    document.body.appendChild(fakeAd);
    
    // Check if the element was removed or hidden
    setTimeout(() => {
      const isBlocked = fakeAd.offsetHeight === 0 || 
                       fakeAd.offsetWidth === 0 || 
                       fakeAd.style.display === 'none' ||
                       fakeAd.style.visibility === 'hidden';
      
      this.isAdBlocked = isBlocked;
      this.notifyCallbacks();
      
      // Clean up
      if (fakeAd.parentNode) {
        fakeAd.parentNode.removeChild(fakeAd);
      }
    }, 100);

    // Method 2: Try to load a known ad script
    const script = document.createElement('script');
    script.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js';
    script.onerror = () => {
      this.isAdBlocked = true;
      this.notifyCallbacks();
    };
    script.onload = () => {
      this.isAdBlocked = false;
      this.notifyCallbacks();
    };
    
    // Add timeout fallback
    setTimeout(() => {
      if (!this.isAdBlocked) {
        this.isAdBlocked = false;
        this.notifyCallbacks();
      }
    }, 2000);
  }

  private notifyCallbacks(): void {
    this.callbacks.forEach(callback => callback(this.isAdBlocked));
  }

  public isBlocked(): boolean {
    return this.isAdBlocked;
  }

  public onDetection(callback: (blocked: boolean) => void): void {
    this.callbacks.push(callback);
    // Call immediately if already detected
    if (this.isAdBlocked !== undefined) {
      callback(this.isAdBlocked);
    }
  }

  public removeCallback(callback: (blocked: boolean) => void): void {
    const index = this.callbacks.indexOf(callback);
    if (index > -1) {
      this.callbacks.splice(index, 1);
    }
  }
}

// Export singleton instance
export const adBlockDetector = AdBlockDetector.getInstance();
