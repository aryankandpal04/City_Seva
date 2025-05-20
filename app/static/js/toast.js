// Toast Notification System

let toastContainer = null;

function initializeToast() {
    // Create toast container if it doesn't exist
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
}

function showToast(message, type = 'info', duration = 3000) {
    if (!toastContainer) {
        initializeToast();
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type} fade-in`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    // Create toast content
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${getToastTitle(type)}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    // Add to container
    toastContainer.appendChild(toast);

    // Show toast
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    // Add close button functionality
    const closeButton = toast.querySelector('.btn-close');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            hideToast(toast);
        });
    }

    // Auto hide after duration
    setTimeout(() => {
        hideToast(toast);
    }, duration);
}

function hideToast(toast) {
    toast.classList.remove('show');
    toast.classList.add('fade-out');
    
    // Remove from DOM after animation
    setTimeout(() => {
        if (toast.parentNode === toastContainer) {
            toastContainer.removeChild(toast);
        }
    }, 300);
}

function getToastTitle(type) {
    switch (type) {
        case 'success':
            return 'Success';
        case 'error':
            return 'Error';
        case 'warning':
            return 'Warning';
        case 'info':
        default:
            return 'Information';
    }
}

// Export functions
window.showToast = showToast;
window.initializeToast = initializeToast; 