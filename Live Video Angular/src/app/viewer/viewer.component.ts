import { Component, ElementRef, OnInit, AfterViewInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../api.service';
import LivePlayer from '@een/live-video-web-sdk'
import Hls from 'hls.js';

@Component({
  selector: 'app-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './viewer.component.html',
  styleUrls: ['./viewer.component.css']
})
export class ViewerComponent implements OnInit, AfterViewInit {
  @ViewChild('loader', { static: true }) loader!: ElementRef<HTMLDivElement>;
  @ViewChild('videoElement', { static: false }) videoElement!: ElementRef<HTMLVideoElement>;

  cameraId: string | null = null;
  camera: any;
  hlsUrl: string = '';
  multipartUrl: string = '';
  hls: Hls | undefined;
  multipart: any;

  constructor (
    private route: ActivatedRoute,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    this.cameraId = this.route.snapshot.paramMap.get('cameraId');
    console.log('Camera ID:', this.cameraId);
  }

  ngAfterViewInit(): void {
    if (this.cameraId) {
      this.loadCameraData();
    }
  }

  private loadCameraData() {
    console.log('Loading camera', this.cameraId);
    this.apiService.getCameras(this.cameraId).subscribe({
      next: (cameraResponse) => {
        const camera = cameraResponse;
        this.apiService.getFeeds(this.cameraId, "main", "multipartUrl,hlsUrl").subscribe({
          next: (feedResponse) => {
            const feeds = feedResponse['results'];
            this.camera = camera;
            this.hlsUrl = feeds[0].hlsUrl;
            this.multipartUrl = feeds[0].multipartUrl;

            // Initialize player after a short delay 
            // to ensure the video element is ready.
            setTimeout(() => {
              this.initializePlayer(this.hlsUrl);
            }, 20);
          },
          error: (error) => {
            console.error('Error loading stream URL.', error);
          }
        })
      },
      error: (error) => {
        console.error('Error loading camera info.', error);
      }
    });
  }

  initializePlayer(videoSrc: string) {
    console.log('Initializing player with', videoSrc);
    const video: HTMLVideoElement = this.videoElement.nativeElement;

    if (Hls.isSupported()) {
      console.log('HLS supported');
      this.hls = new Hls({
        xhrSetup: (xhr) => {
          xhr.setRequestHeader('Authorization', `Bearer ${this.apiService.getAccessToken()}`);
        }
      });
      this.hls.loadSource(videoSrc);
      this.hls.attachMedia(video);
      video.play();
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = videoSrc;
      video.play();
    }

    // Hide loader when video can play
    video.addEventListener('canplay', () => this.hideLoader());

    // Fallback to hide loader after a timeout.
    setTimeout(() => this.hideLoader(), 20000);
  }

  hideLoader() {
    this.loader.nativeElement.style.display = 'none';
  }

  switchStream(type: 'hls' | 'multipart') {
    const video: HTMLVideoElement = this.videoElement.nativeElement;
    if (type === 'hls' && this.hls) {
      this.hls.loadSource(this.hlsUrl);
      this.hls.attachMedia(video);
    } else if (type === 'multipart') {
      if (this.multipart) {
        this.multipart.stop();
      }

      const config = {
        videoElement: video,
        cameraId: this.cameraId,
        baseUrl: this.apiService.getBaseUrl(),
        jwt: this.apiService.getAccessToken(),
        onFrame: (time: any) => console.log('Frame time:', time),
      };
      console.log('Starting multipart stream with config:', config);
      this.multipart = new LivePlayer();
      this.multipart.start(config);

    }

    this.updateButtonState(type);
  }

  updateButtonState(type: 'hls' | 'multipart') {
    const hlsBtn = document.getElementById('hlsBtn');
    const multipartBtn = document.getElementById('multipartBtn');
    if (type === 'hls') {
      hlsBtn?.classList.add('active');
      multipartBtn?.classList.remove('active');
    } else {
      multipartBtn?.classList.add('active');
      hlsBtn?.classList.remove('active');
    }
  }
}
