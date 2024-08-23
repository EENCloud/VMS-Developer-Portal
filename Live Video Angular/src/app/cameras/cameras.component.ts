import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { ApiService } from '../api.service';

@Component({
  selector: 'app-cameras',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './cameras.component.html',
  styles: ``
})
export class CamerasComponent implements OnInit {
  code: string | null = null;
  cameras: any[] = [];
  error: string | undefined;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    this.code = this.route.snapshot.queryParamMap.get('code');

    if (this.code) {
      this.router.navigate(
        ['/login'],
        { queryParams: { code: this.code } }
      );
    }

    // Load camera data
    this.loadCamerasAndFeeds();
  }

  private loadCamerasAndFeeds() {
    console.log('Loading cameras and feeds');
    this.apiService.getCameras(null).subscribe({
      next: (cameraResponse) => {
        const cameras = cameraResponse.results;
        this.apiService.getFeeds(null).subscribe({
          next: (feedResponse) => {
            const feeds = feedResponse.results;
            const cameraDict = cameras.reduce((acc: any, camera: any) => {
              acc[camera.id] = camera;
              return acc;
            }, {});

            feeds.forEach((feed: any) => {
              const camera = cameraDict[feed.deviceId];
              if (camera && !camera.multipartUrl) {
                camera.multipartUrl = feed.multipartUrl;
              }
            });

            this.cameras = Object.values(cameraDict).slice(0, 12);
          },
          error: (error) => {
            console.error('Failed to get feeds', error);
          },
          complete: () => {
            console.log('Completed');
          }
        });
      },
      error: (error) => {
        console.error('Failed to get cameras', error);
      }
    });
  }

}

