self.addEventListener('push', function(event) {
    let data = {};
    
    // Attempt to parse the incoming string into a JSON object
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        // Fallback if the data is sent as a plain string
        data = { 
            title: "🚀 XCEED | Next Class", 
            body: event.data ? event.data.text() : "Class starting soon!" 
        };
    }
    
    const options = {
        body: data.body || "Your next class is starting!",
        icon: '/static/xceed-logo.png',
        badge: '/static/xceed-logo.png',
        vibrate: [200, 100, 200],
        tag: 'xceed-alert',
        renotify: true
    };

    event.waitUntil(
        self.registration.showNotification(data.title || "XCEED Alert", options)
    );
});

// Handle Button Clicks
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.action === 'open_url') {
        event.waitUntil(clients.openWindow('https://xceed.nitj.ac.in/timetable'));
    }
});