// Main JavaScript for CitySeva Web Application

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeNavbar();
    initializeToast();
    initializeLazyLoading();
    initializeInfiniteScroll();
});

// Initialize Navbar
function initializeNavbar() {
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Initialize Bootstrap dropdowns
    const dropdownElementList = document.querySelectorAll('.dropdown-toggle');
    const dropdownList = [...dropdownElementList].map(dropdownToggleEl => {
        return new bootstrap.Dropdown(dropdownToggleEl, {
            offset: [0, 8],
            boundary: 'viewport'
        });
    });

    // Handle all navbar buttons and links
    document.querySelectorAll('.navbar .btn, .navbar .nav-link').forEach(element => {
        element.addEventListener('click', function(e) {
            // If it's a dropdown toggle, let Bootstrap handle it
            if (this.classList.contains('dropdown-toggle')) {
                return;
            }
            
            // For regular links and buttons, ensure they work
            if (this.getAttribute('href') && this.getAttribute('href') !== '#') {
                window.location.href = this.getAttribute('href');
            }
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.matches('.dropdown-toggle') && !e.target.closest('.dropdown-menu')) {
            dropdownList.forEach(dropdown => {
                dropdown.hide();
            });
        }
    });
}

// Initialize Toast
function initializeToast() {
    // Create toast container if it doesn't exist
    if (!document.getElementById('toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
}

// Show Toast Message
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

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
    const submitButton = form.querySelector('button[type="submit"]');
    
    // Validate form
    if (!validateForm(form)) {
        return;
    }
    
    // Disable submit button and show loading state
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
    }
    
    // Create FormData object
    const formData = new FormData(form);
    
    // Submit form data
    fetch(form.action, {
        method: form.method,
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(async response => {
        const contentType = response.headers.get('content-type');
        if (!response.ok) {
            if (contentType && contentType.includes('application/json')) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Error submitting form');
            } else {
                throw new Error('Server error occurred');
            }
        }
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // If not JSON, redirect to the response URL
            window.location.href = response.url;
            return null;
        }
    })
    .then(data => {
        if (!data) return; // Skip if we redirected
        
        if (data.success) {
            showToast(data.message || 'Form submitted successfully', 'success');
            if (data.redirect) {
                window.location.href = data.redirect;
            } else {
                form.reset();
            }
        } else {
            showToast(data.message || 'Error submitting form', 'error');
            // Display validation errors if present
            if (data.errors) {
                Object.keys(data.errors).forEach(field => {
                    const input = form.querySelector(`[name="${field}"]`);
                    if (input) {
                        input.classList.add('is-invalid');
                        const feedback = input.nextElementSibling;
                        if (feedback && feedback.classList.contains('invalid-feedback')) {
                            feedback.textContent = data.errors[field].join(', ');
                        }
                    }
                });
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast(error.message || 'An error occurred while submitting the form', 'error');
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

// Function to add animation classes to elements when they come into view
function initializeScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    
    if (!animatedElements.length) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const animation = el.dataset.animation || 'fadeIn';
                const delay = el.dataset.delay || 0;
                
                setTimeout(() => {
                    el.classList.add('animated', animation);
                    el.style.opacity = 1;
                }, delay);
                
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.1 });
    
    animatedElements.forEach(el => {
        el.style.opacity = 0;
        observer.observe(el);
    });
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
        zoom: 5,
        styles: [
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{"color": "#e9e9e9"}, {"lightness": 17}]
            },
            {
                "featureType": "landscape",
                "elementType": "geometry",
                "stylers": [{"color": "#f5f5f5"}, {"lightness": 20}]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.fill",
                "stylers": [{"color": "#ffffff"}, {"lightness": 17}]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [{"color": "#ffffff"}, {"lightness": 29}, {"weight": 0.2}]
            },
            {
                "featureType": "road.arterial",
                "elementType": "geometry",
                "stylers": [{"color": "#ffffff"}, {"lightness": 18}]
            },
            {
                "featureType": "road.local",
                "elementType": "geometry",
                "stylers": [{"color": "#ffffff"}, {"lightness": 16}]
            },
            {
                "featureType": "poi",
                "elementType": "geometry",
                "stylers": [{"color": "#f5f5f5"}, {"lightness": 21}]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry",
                "stylers": [{"color": "#dedede"}, {"lightness": 21}]
            },
            {
                "featureType": "administrative",
                "elementType": "geometry.stroke",
                "stylers": [{"color": "#fefefe"}, {"lightness": 17}, {"weight": 1.2}]
            }
        ]
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
            map: map,
            animation: google.maps.Animation.DROP
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
                map: map,
                animation: google.maps.Animation.DROP
            });
        }
        
        // Check if location element exists
        const locationInput = document.getElementById('location');
        if (!locationInput) return;
        
        // Animate location input to show it's being updated
        locationInput.classList.add('is-loading');
        
        // Reverse geocode to get address
        const geocoder = new google.maps.Geocoder();
        geocoder.geocode({ location: e.latLng }, function(results, status) {
            if (status === 'OK' && results[0]) {
                locationInput.value = results[0].formatted_address;
                locationInput.classList.add('is-valid');
            }
            locationInput.classList.remove('is-loading');
        });
    });
    
    // Add form validation for complaint submission
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!latInput.value || !lngInput.value) {
                event.preventDefault();
                
                // Create and show alert
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-danger animate-fade-in mt-3';
                alertDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i> Please select a location on the map. This is required for verification purposes.';
                
                const mapContainer = document.getElementById('complaint-map').parentElement;
                mapContainer.insertAdjacentElement('afterend', alertDiv);
                
                // Scroll to map with smooth animation
                document.getElementById('complaint-map').scrollIntoView({ 
                    behavior: 'smooth',
                    block: 'center'
                });
                
                // Remove alert after 5 seconds
                setTimeout(() => {
                    alertDiv.remove();
                }, 5000);
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
    
    // Chart.js animation options
    const animationOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 2000,
            easing: 'easeOutQuart'
        },
        plugins: {
            legend: {
                position: 'bottom'
            }
        }
    };
    
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
                                    '#00bcd4', '#3f51b5', '#03a9f4', '#ff9800', 
                                    '#f44336', '#4caf50', '#9c27b0', '#e91e63'
                                ],
                                borderWidth: 2,
                                borderColor: '#ffffff'
                            }]
                        },
                        options: {
                            ...animationOptions,
                            plugins: {
                                ...animationOptions.plugins,
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${label}: ${value} (${percentage}%)`;
                                        }
                                    }
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
                                    '#4caf50', '#ff9800', '#f44336', '#8b0000'
                                ],
                                borderWidth: 2,
                                borderColor: '#ffffff'
                            }]
                        },
                        options: {
                            ...animationOptions,
                            cutout: '70%',
                            plugins: {
                                ...animationOptions.plugins,
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${label}: ${value} (${percentage}%)`;
                                        }
                                    }
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
                                borderColor: index === 0 ? '#00bcd4' : '#4caf50',
                                backgroundColor: index === 0 ? 'rgba(0, 188, 212, 0.1)' : 'rgba(76, 175, 80, 0.1)',
                                borderWidth: 3,
                                pointBackgroundColor: index === 0 ? '#00bcd4' : '#4caf50',
                                pointRadius: 4,
                                pointHoverRadius: 6,
                                fill: true,
                                tension: 0.3
                            }))
                        },
                        options: {
                            ...animationOptions,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }
                                },
                                x: {
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching timeline data:', error));
    }
}

// Function to initialize enhanced form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form.needs-validation');
    
    if (!forms.length) return;
    
    forms.forEach(form => {
        // Add submit event listener
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Find the first invalid element and focus it
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    
                    // Scroll to the invalid element with smooth animation
                    firstInvalid.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Add input event listeners for real-time validation
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });
}

// Function to initialize animated counters
function initializeCounters() {
    const counters = document.querySelectorAll('.counter');
    
    if (!counters.length) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseInt(counter.getAttribute('data-target'));
                const duration = parseInt(counter.getAttribute('data-duration') || 2000);
                const increment = target / (duration / 16); // 60fps
                
                let current = 0;
                const updateCounter = () => {
                    current += increment;
                    if (current < target) {
                        counter.textContent = Math.ceil(current);
                        requestAnimationFrame(updateCounter);
                    } else {
                        counter.textContent = target;
                    }
                };
                
                updateCounter();
                observer.unobserve(counter);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => {
        observer.observe(counter);
    });
}

// Function to initialize the complaints map
function initializeComplaintsMap() {
    const mapElement = document.getElementById('complaints-map');
    if (!mapElement) return;
    
    const complaintsData = JSON.parse(mapElement.getAttribute('data-complaints') || '[]');
    if (!complaintsData.length) return;
    
    // Initialize the map
    const map = new google.maps.Map(mapElement, {
        center: { lat: 20.5937, lng: 78.9629 }, // Default center on India
        zoom: 5,
        styles: [
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{"color": "#e9e9e9"}, {"lightness": 17}]
            },
            {
                "featureType": "landscape",
                "elementType": "geometry",
                "stylers": [{"color": "#f5f5f5"}, {"lightness": 20}]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.fill",
                "stylers": [{"color": "#ffffff"}, {"lightness": 17}]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [{"color": "#ffffff"}, {"lightness": 29}, {"weight": 0.2}]
            },
            {
                "featureType": "road.arterial",
                "elementType": "geometry",
                "stylers": [{"color": "#ffffff"}, {"lightness": 18}]
            },
            {
                "featureType": "road.local",
                "elementType": "geometry",
                "stylers": [{"color": "#ffffff"}, {"lightness": 16}]
            },
            {
                "featureType": "poi",
                "elementType": "geometry",
                "stylers": [{"color": "#f5f5f5"}, {"lightness": 21}]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry",
                "stylers": [{"color": "#dedede"}, {"lightness": 21}]
            },
            {
                "featureType": "administrative",
                "elementType": "geometry.stroke",
                "stylers": [{"color": "#fefefe"}, {"lightness": 17}, {"weight": 1.2}]
            }
        ]
    });
    
    // Add markers for each complaint
    const bounds = new google.maps.LatLngBounds();
    const infoWindow = new google.maps.InfoWindow();
    
    complaintsData.forEach(complaint => {
        const position = { lat: parseFloat(complaint.latitude), lng: parseFloat(complaint.longitude) };
        
        // Skip if invalid coordinates
        if (isNaN(position.lat) || isNaN(position.lng)) return;
        
        // Add marker
        const marker = new google.maps.Marker({
            position,
            map,
            title: complaint.title,
            animation: google.maps.Animation.DROP,
            icon: {
                url: getMarkerIconByStatus(complaint.status),
                scaledSize: new google.maps.Size(30, 30)
            }
        });
        
        // Extend bounds
        bounds.extend(position);
        
        // Add click listener
        marker.addListener('click', () => {
            // Create info window content
            const content = `
                <div class="info-window">
                    <h5>${complaint.title}</h5>
                    <p><strong>Status:</strong> <span class="status-badge status-${complaint.status.toLowerCase()}">${complaint.status}</span></p>
                    <p><strong>Category:</strong> ${complaint.category}</p>
                    <p><strong>Location:</strong> ${complaint.location}</p>
                    <a href="/complaint/${complaint.id}" class="btn btn-sm btn-primary">View Details</a>
                </div>
            `;
            
            infoWindow.setContent(content);
            infoWindow.open(map, marker);
        });
    });
    
    // Fit map to bounds if we have valid complaints
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
        
        // Don't zoom in too far
        const listener = google.maps.event.addListener(map, 'idle', function() {
            if (map.getZoom() > 15) {
                map.setZoom(15);
            }
            google.maps.event.removeListener(listener);
        });
    }
}

// Helper function to get marker icon based on complaint status
function getMarkerIconByStatus(status) {
    switch (status.toLowerCase()) {
        case 'pending':
            return 'https://maps.google.com/mapfiles/ms/icons/yellow-dot.png';
        case 'in progress':
            return 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png';
        case 'resolved':
            return 'https://maps.google.com/mapfiles/ms/icons/green-dot.png';
        case 'rejected':
            return 'https://maps.google.com/mapfiles/ms/icons/red-dot.png';
        default:
            return 'https://maps.google.com/mapfiles/ms/icons/purple-dot.png';
    }
}

// Initialize all components when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    
    // Initialize all components
    initializeToasts();
    initializeScrollAnimations();
    initializeComplaintMap();
    initializeDashboardCharts();
    initializeFormValidation();
    initializeCounters();
    initializeComplaintsMap();
    
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return; // Skip empty href
            
            const target = document.querySelector(href);
            if (!target) return;
            
            e.preventDefault();
            
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        });
    });
}); 