// Infinite Scroll Implementation
document.addEventListener('DOMContentLoaded', function() {
    const infiniteScrollContainers = document.querySelectorAll('[data-infinite-scroll]');
    
    infiniteScrollContainers.forEach(container => {
        let page = 1;
        let loading = false;
        let hasMore = true;
        
        const loadMore = async () => {
            if (loading || !hasMore) return;
            
            loading = true;
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'text-center py-3';
            loadingIndicator.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
            container.appendChild(loadingIndicator);
            
            try {
                const response = await fetch(`${container.dataset.infiniteScroll}?page=${page + 1}`);
                const data = await response.json();
                
                if (data.items && data.items.length > 0) {
                    data.items.forEach(item => {
                        const element = document.createElement('div');
                        element.className = container.dataset.itemClass || '';
                        element.innerHTML = item.html;
                        container.insertBefore(element, loadingIndicator);
                    });
                    
                    page++;
                    hasMore = data.has_more;
                } else {
                    hasMore = false;
                }
            } catch (error) {
                console.error('Error loading more items:', error);
            } finally {
                loading = false;
                loadingIndicator.remove();
            }
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && hasMore) {
                    loadMore();
                }
            });
        }, {
            root: null,
            rootMargin: '100px',
            threshold: 0.1
        });
        
        const sentinel = document.createElement('div');
        sentinel.className = 'infinite-scroll-sentinel';
        container.appendChild(sentinel);
        observer.observe(sentinel);
    });
}); 