#include <gtk/gtk.h>
#include <webkit2/webkit2.h>

static void destroyWindowCallback(GtkWidget* widget, gpointer data) {
    gtk_main_quit();
}

static void loadChangedCallback(WebKitWebView* webView, WebKitLoadEvent loadEvent, gpointer data) {
    const gchar* uri = webkit_web_view_get_uri(webView);
    if (g_str_has_prefix(uri, "https://example.com/oauth2/callback")) {
        // Extract the authorization code from the URL and use it to obtain an access token
        // ...
        // Close the browser window
        gtk_widget_destroy(GTK_WIDGET(gtk_widget_get_toplevel(GTK_WIDGET(webView))));
    }
}

int main(int argc, char* argv[]) {
    gtk_init(&argc, &argv);

    GtkWidget* window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "Mini Browser");
    gtk_window_set_default_size(GTK_WINDOW(window), 800, 600);
    g_signal_connect(window, "destroy", G_CALLBACK(destroyWindowCallback), NULL);

    WebKitWebView* webView = WEBKIT_WEB_VIEW(webkit_web_view_new());
    gtk_container_add(GTK_CONTAINER(window), GTK_WIDGET(webView));
    webkit_web_view_load_uri(webView, "https://example.com/oauth2/auth");

    g_signal_connect(webView, "load-changed", G_CALLBACK(loadChangedCallback), NULL);

    gtk_widget_show_all(window);

    gtk_main();
    return 0;
}
