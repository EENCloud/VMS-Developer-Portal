import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [],
  template: `
        <h1>Sign In</h1>
        <br />
        <a [href]="authUrl">Login with Eagle Eye Networks</a>
  `,
  styles: ``
})
export class LoginComponent implements OnInit {
  authUrl: string | undefined;
  code: string | null = null;

  constructor(
    private authService: AuthService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit() {
    this.authUrl = this.authService.getAuthUrl();
    this.code = this.route.snapshot.queryParamMap.get('code');

    if (this.code) {
      this.authService.exchangeToken(this.code).subscribe({
        next: (response: any) => {
          console.log(response);
          this.authService.storeSession(response);
          this.router.navigate(['/']);
        },
        error: (error) => {
          console.error('Authentication failed', error);
        },
        complete: () => {
          console.log('Authentication complete');
        }
      });
    }
  }
}
