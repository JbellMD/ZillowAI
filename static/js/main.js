/**
 * Main JavaScript file for ZillowAI
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length) {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Price range validator
    const minPriceInput = document.getElementById('min_price');
    const maxPriceInput = document.getElementById('max_price');
    
    if (minPriceInput && maxPriceInput) {
        const validatePriceRange = function() {
            const minPrice = parseInt(minPriceInput.value) || 0;
            const maxPrice = parseInt(maxPriceInput.value) || 0;
            
            if (maxPrice > 0 && minPrice > maxPrice) {
                maxPriceInput.setCustomValidity('Maximum price cannot be less than minimum price');
            } else {
                maxPriceInput.setCustomValidity('');
            }
        };
        
        minPriceInput.addEventListener('change', validatePriceRange);
        maxPriceInput.addEventListener('change', validatePriceRange);
    }

    // Property card hover effects
    const propertyCards = document.querySelectorAll('.property-card');
    
    propertyCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });

    // Save search form validation
    const saveSearchForm = document.querySelector('form[action="/save"]');
    
    if (saveSearchForm) {
        saveSearchForm.addEventListener('submit', function(e) {
            const searchName = document.getElementById('search_name').value.trim();
            
            if (!searchName) {
                e.preventDefault();
                alert('Please enter a name for your saved search');
                return false;
            }
            
            return true;
        });
    }

    // Mobile menu collapse after click
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarCollapse) {
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 992) {
                    const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                    bsCollapse.hide();
                }
            });
        });
    }

    // Carousel auto-play control
    const propertyCarousel = document.getElementById('propertyImageCarousel');
    
    if (propertyCarousel) {
        const carousel = new bootstrap.Carousel(propertyCarousel, {
            interval: 5000,
            wrap: true
        });
        
        // Pause carousel on mouse enter, resume on mouse leave
        propertyCarousel.addEventListener('mouseenter', () => {
            carousel.pause();
        });
        
        propertyCarousel.addEventListener('mouseleave', () => {
            carousel.cycle();
        });
    }
});
