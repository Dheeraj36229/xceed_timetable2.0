self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : { title: "XCEED Alert", body: "Class starting soon!" };
    
    const options = {
        body: data.body,
        // Make sure these images exist in your /static/ folder
        icon: '/static/xceed-logo.png',     // High-res logo (192x192)
        badge: '/static/xceed-badge.png',   // Small monochrome icon for Android status bar
        image: '/static/xceed-banner.png',  // Optional: A wide banner (e.g., campus photo)
        
        vibrate: [200, 100, 200, 100, 400], // Custom Xceed vibration rhythm
        tag: 'xceed-class-alert',           // Overwrites old alerts so they don't stack
        renotify: true,                     // Vibrates even if an old alert is still visible
        
        actions: [
            { action: 'open_url', title: 'Open Timetable', icon: '/static/open-icon.png' },
            { action: 'close', title: 'Dismiss' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Handle Button Clicks
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.action === 'open_url') {
        event.waitUntil(clients.openWindow('https://xceed.nitj.ac.in/timetable'));
    }
});