import { Component } from '@angular/core';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-logout',
  standalone: true,
  imports: [],
  template: `
    <p>Logging out...</p>
  `,
  styles: ``
})
export class LogoutComponent {
  constructor(private authService: AuthService) { 
    this.authService.logout();
  }
}
