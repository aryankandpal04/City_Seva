// Main JavaScript for CitySeva Web Application

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeNavbar();
    initializeToast();
    initializeLazyLoading();
    initializeInfiniteScroll();
});

// Lazy Loading Images
function initializeLazyLoading() {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    
    if ('loading' in HTMLImageElement.prototype) {
        // Browser supports native lazy loading
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
        });
    } else {
        // Fallback for browsers that don't support lazy loading
        const lazyLoadObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    observer.unobserve(img);
                }
            });
        });

        lazyImages.forEach(img => {
            lazyLoadObserver.observe(img);
        });
    }
}

// Infinite Scroll
function initializeInfiniteScroll() {
    const options = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const loadMoreButton = entry.target;
                if (loadMoreButton.dataset.page) {
                    loadMoreContent(loadMoreButton.dataset.page);
                }
            }
        });
    }, options);

    const loadMoreTriggers = document.querySelectorAll('.load-more-trigger');
    loadMoreTriggers.forEach(trigger => observer.observe(trigger));
}

// Load More Content
async function loadMoreContent(page) {
    try {
        const response = await fetch(`/api/load-more?page=${page}`);
        const data = await response.json();
        
        if (data.content) {
            const container = document.querySelector('.content-container');
            container.insertAdjacentHTML('beforeend', data.content);
            
            // Update page number for next load
            const loadMoreTrigger = document.querySelector('.load-more-trigger');
            if (loadMoreTrigger) {
                loadMoreTrigger.dataset.page = parseInt(page) + 1;
            }
        }
    } catch (error) {
        console.error('Error loading more content:', error);
        showToast('Error loading more content', 'error');
    }
}

// Form Validation
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Handle Form Submission
function handleFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    if (!validateForm(form)) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
    }

    // Submit form data
    fetch(form.action, {
        method: form.method,
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message || 'Form submitted successfully', 'success');
            form.reset();
        } else {
            showToast(data.message || 'Error submitting form', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while submitting the form', 'error');
    })
    .finally(() => {
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = submitButton.dataset.originalText || 'Submit';
        }
    });
}

// Initialize Form Handlers
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', handleFormSubmit);
    
    // Store original button text
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.dataset.originalText = submitButton.innerHTML;
    }
});

// Custom JavaScript for CitySeva Web Application

// Function to initialize the toast messages
function initializeToasts() {
    const toastElList = document.querySelectorAll('.toast');
    const toastList = [...toastElList].map(toastEl => new bootstrap.Toast(toastEl));
    toastList.forEach(toast => toast.show());
}

// Function to initialize the complaint submission map
function initializeComplaintMap() {
    // Check if the map element exists
    const mapElement = document.getElementById('complaint-map');
    if (!mapElement) return;

    // Check if latitude and longitude inputs exist
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    
    if (!latInput || !lngInput) return; // Exit if these elements don't exist

    // Initialize the map with Google Maps
    const map = new google.maps.Map(mapElement, {
        center: { lat: 20.5937, lng: 78.9629 }, // Default center on India
        zoom: 5
    });

    // Add marker for the complaint location (if editing a complaint)
    let marker;
    if (latInput.value && lngInput.value) {
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        
        map.setCenter({ lat, lng });
        map.setZoom(15);
        
        marker = new google.maps.Marker({
            position: { lat, lng },
            map: map
        });
    }

    // Handle map clicks to set location
    map.addListener('click', function(e) {
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        
        // Update hidden form fields
        latInput.value = lat;
        lngInput.value = lng;
        
        // Update or add marker
        if (marker) {
            marker.setPosition(e.latLng);
        } else {
            marker = new google.maps.Marker({
                position: e.latLng,
                map: map
            });
        }
        
        // Check if location element exists
        const locationInput = document.getElementById('location');
        if (!locationInput) return;
        
        // Reverse geocode to get address
        const geocoder = new google.maps.Geocoder();
        geocoder.geocode({ location: e.latLng }, function(results, status) {
            if (status === 'OK' && results[0]) {
                locationInput.value = results[0].formatted_address;
            }
        });
    });
    
    // Add form validation for complaint submission
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!latInput.value || !lngInput.value) {
                event.preventDefault();
                alert('Please select a location on the map. This is required for verification purposes.');
                document.getElementById('complaint-map').scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
}

// Function to initialize the dashboard charts
function initializeDashboardCharts() {
    // Check if we're on the dashboard page
    const categoryChartElement = document.getElementById('categoryChart');
    const priorityChartElement = document.getElementById('priorityChart');
    const timelineChartElement = document.getElementById('timelineChart');
    
    if (!categoryChartElement && !priorityChartElement && !timelineChartElement) return;
    
    // Fetch the category data
    if (categoryChartElement) {
        fetch('/api/stats/category')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    new Chart(categoryChartElement, {
                        type: 'pie',
                        data: {
                            labels: data.data.labels,
                            datasets: [{
                                data: data.data.values,
                                backgroundColor: [
                                    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', 
                                    '#e74a3b', '#858796', '#5a5c69', '#f8f9fc'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom'
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching category data:', error));
    }
    
    // Fetch the priority data
    if (priorityChartElement) {
        fetch('/api/stats/priority')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    new Chart(priorityChartElement, {
                        type: 'doughnut',
                        data: {
                            labels: data.data.labels,
                            datasets: [{
                                data: data.data.values,
                                backgroundColor: [
                                    '#5cb85c', '#f0ad4e', '#d9534f', '#8b0000'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom'
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching priority data:', error));
    }
    
    // Fetch the timeline data
    if (timelineChartElement) {
        fetch('/api/stats/timeline')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    new Chart(timelineChartElement, {
                        type: 'line',
                        data: {
                            labels: data.data.labels,
                            datasets: data.data.datasets.map((dataset, index) => ({
                                label: dataset.label,
                                data: dataset.data,
                                borderColor: index === 0 ? '#4e73df' : '#1cc88a',
                                backgroundColor: 'transparent',
                                borderWidth: 2,
                                pointBackgroundColor: index === 0 ? '#4e73df' : '#1cc88a',
                                tension: 0.3
                            }))
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching timeline data:', error));
    }
}

// Function to initialize the complaints map
function initializeComplaintsMap() {
    // Check if the map element exists
    const mapElement = document.getElementById('complaints-map');
    if (!mapElement) return;
    
    // Initialize the map with Google Maps
    const map = new google.maps.Map(mapElement, {
        center: { lat: 20.5937, lng: 78.9629 }, // Default center on India
        zoom: 5
    });
    
    // Fetch complaint data for the map
    fetch('/api/map/complaints')
        .then(response => response.json())
        .then(data => {
            // Create bounds to fit all markers
            const bounds = new google.maps.LatLngBounds();
            
            // Add markers for each complaint
            if (data.features && data.features.length > 0) {
                data.features.forEach(feature => {
                    // Get coordinates
                    const lng = feature.geometry.coordinates[0];
                    const lat = feature.geometry.coordinates[1];
                    const position = new google.maps.LatLng(lat, lng);
                    
                    // Choose marker color based on status
                    let markerColor = '#f0ad4e'; // Default/pending - yellow
                    if (feature.properties.status === 'in_progress') {
                        markerColor = '#5bc0de'; // Blue
                    } else if (feature.properties.status === 'resolved') {
                        markerColor = '#5cb85c'; // Green
                    } else if (feature.properties.status === 'rejected') {
                        markerColor = '#d9534f'; // Red
                    }
                    
                    // Create marker using custom SVG icon
                    const marker = new google.maps.Marker({
                        position: position,
                        map: map,
                        title: feature.properties.title,
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            fillColor: markerColor,
                            fillOpacity: 0.8,
                            strokeWeight: 1,
                            strokeColor: '#FFFFFF',
                            scale: 10
                        }
                    });
                    
                    // Create info window content
                    const contentString = `
                        <div>
                            <strong>${feature.properties.title}</strong><br>
                            Category: ${feature.properties.category}<br>
                            Status: ${feature.properties.status}<br>
                            Priority: ${feature.properties.priority}<br>
                            Date: ${feature.properties.created_at}<br>
                            <a href="/complaint/${feature.properties.id}" class="btn btn-sm btn-primary mt-2">View Details</a>
                        </div>
                    `;
                    
                    // Create info window
                    const infoWindow = new google.maps.InfoWindow({
                        content: contentString
                    });
                    
                    // Add click listener to open info window
                    marker.addListener('click', function() {
                        infoWindow.open(map, marker);
                    });
                    
                    // Extend bounds to include this marker
                    bounds.extend(position);
                });
                
                // Fit the map to show all markers
                map.fitBounds(bounds);
                
                // If only one marker, zoom out a bit
                if (data.features.length === 1) {
                    google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
                        map.setZoom(Math.min(15, map.getZoom()));
                    });
                }
            }
        })
        .catch(error => console.error('Error fetching map data:', error));
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize toast messages
    initializeToasts();
    
    // Initialize complaint submission map
    initializeComplaintMap();
    
    // Initialize dashboard charts
    initializeDashboardCharts();
    
    // Initialize complaints map
    initializeComplaintsMap();
    
    // Handle complaint status updates via API
    const statusUpdateButtons = document.querySelectorAll('.update-status-btn');
    statusUpdateButtons.forEach(button => {
        button.addEventListener('click', function() {
            const complaintId = this.dataset.complaintId;
            const newStatus = this.dataset.status;
            const comment = prompt("Enter a comment for this status update (optional):");
            
            if (complaintId && newStatus) {
                fetch(`/api/complaints/${complaintId}/status`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        status: newStatus,
                        comment: comment || `Status updated to ${newStatus}`
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Reload the page to show updated status
                        window.location.reload();
                    } else {
                        alert("Error updating complaint status: " + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error updating status:', error);
                    alert("Error updating complaint status. Please try again.");
                });
            }
        });
    });
}); 