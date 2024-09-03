import { Routes } from '@angular/router';
import { AuthGuard } from './auth/auth.guard';
import { CamerasComponent } from './cameras/cameras.component';
import { ViewerComponent } from './viewer/viewer.component';
import { LoginComponent } from './login/login.component';
import { LogoutComponent } from './logout/logout.component';

const routeConfig: Routes = [
    {
        path: '',
        component: CamerasComponent,
        title: 'Camera Select',
        canActivate: [AuthGuard],
    },
    {
        path: 'view/:cameraId',
        component: ViewerComponent,
        title: 'Live View',
        canActivate: [AuthGuard],
    },
    {
        path: 'login',
        component: LoginComponent,
        title: 'Login'
    },
    {
        path: 'logout',
        component: LogoutComponent
    }
];

export default routeConfig;