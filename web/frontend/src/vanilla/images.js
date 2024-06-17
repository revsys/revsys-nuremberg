import DownloadQueue from './download-queue'

export default class Image {
  constructor(options) {
    // Set some image defaults
    Object.assign(this,
      {
        scale: 1,
        visible: false,
        preload: false,
        loader: null,
        cache: {}
      }, options)
  }

  init() {
    let img = $('<img></img>').appendTo(this.$el)
    this.img = img[0];

    let aspectRatio = this.size.height / this.size.width

    let spacer = $('<div class="aspect-ratio-spacer"></div>').css({
      'margin-top': aspectRatio * 100 + '%'
    })
    this.$el.append(spacer)

    this.$el.find('img').css({
      'border-bottom-width': aspectRatio * 5 + 'px'
    })
      .toggleClass('aspect-ratio-wide', aspectRatio < 11 / 8.5)
      .attr('alt', this.alt)

    if (!Modernizr.touchevents) {
      this.preloadImage('thumb')
    }
  }

  handleVisible() {
    _.defer(() => {
      if (this.visible) {
        let scale = this.scale
        if (this.$el.width() > this.size.width || scale > 2) {
          this.preloadImage('full')
        } else if (this.$el.width() < 250) {
          this.preloadImage('thumb')
        } else {
          this.preloadImage('screen')
        }
      }
    })
  }

  downloadProgress(e) {
    this.percentLoaded = (e.loaded / (e.total || 150 * 1024)) * 100;
  }

  preloadImage(size) {
    if (this.loader) {
      if (this.loader.size == size) {
        DownloadQueue.refresh(this.loader)
        return
      } else {
        this.loader.cancel()
      }
    }

    let sizes = ['thumb', 'screen', 'full', 'screen', 'thumb']
    let url;
    for (let i = sizes.indexOf(size); i < sizes.length; i++) {
      size = sizes[i]
      url = this.urls[size]
      if (url) {
        break
      }
    }

    sizes = ['thumb', 'screen', 'full'];
    let cached;
    for (let i = sizes.indexOf(size); i < sizes.length; i++) {
      cached = cached || this.cache[sizes[i]]
      if (cached) {
        break
      }
    }

    if (cached) {
      this.url = cached;
      this.preloaded = size
      return;
    }

    this.preloaded = null
    this.loader = DownloadQueue.download(url, this.img)

    this.loader.size = size
    this.loader.progress(this.downloadProgress).then((response) => {
      if (response == "fallback") {
        this.cache[size] = this.img.src
        this.url = this.img.src
        this.preloaded = size
        this.loader = null
      } else {
        let reader = new FileReader
        reader.readAsDataURL(response)
        reader.onload = () => {
          this.cache[size] = reader.result
          this.url = reader.result
          this.preloaded = size
          this.loader = null
        }
      }
    })
      .fail((error) => {
        console.log("preloadImage failed!")
        console.dir(this)
        this.loader = null
      })

  }
}