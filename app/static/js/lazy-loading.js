// Lazy Loading Implementation
document.addEventListener('DOMContentLoaded', function() {
    const lazyImages = document.querySelectorAll('img[data-src]');
    const lazyIframes = document.querySelectorAll('iframe[data-src]');
    
    const lazyLoadObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                
                if (element.tagName.toLowerCase() === 'img') {
                    element.src = element.dataset.src;
                    if (element.dataset.srcset) {
                        element.srcset = element.dataset.srcset;
                    }
                    element.classList.add('loaded');
                } else if (element.tagName.toLowerCase() === 'iframe') {
                    element.src = element.dataset.src;
                    element.classList.add('loaded');
                }
                
                observer.unobserve(element);
            }
        });
    }, {
        root: null,
        rootMargin: '50px',
        threshold: 0.1
    });
    
    // Observe images
    lazyImages.forEach(image => {
        lazyLoadObserver.observe(image);
    });
    
    // Observe iframes
    lazyIframes.forEach(iframe => {
        lazyLoadObserver.observe(iframe);
    });
    
    // Add loading animation
    const style = document.createElement('style');
    style.textContent = `
        img[data-src], iframe[data-src] {
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        
        img.loaded, iframe.loaded {
            opacity: 1;
        }
        
        .lazy-load-placeholder {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
        }
        
        @keyframes loading {
            0% {
                background-position: 200% 0;
            }
            100% {
                background-position: -200% 0;
            }
        }
    `;
    document.head.appendChild(style);
}); 