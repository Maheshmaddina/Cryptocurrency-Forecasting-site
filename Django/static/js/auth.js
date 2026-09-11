// Authentication pages JavaScript for FutureCoin

document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation
    initFormValidation();
    
    // Add input focus effects
    initInputEffects();
    
    // Initialize profile page animations if on profile page
    if (document.querySelector('.profile-container')) {
        initProfileAnimations();
    }
});

// Function to initialize form validation
function initFormValidation() {
    const authForms = document.querySelectorAll('.auth-form');
    
    authForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Get all required inputs
            const requiredInputs = form.querySelectorAll('input[required]');
            
            // Check each required input
            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    showInputError(input, 'This field is required');
                } else {
                    clearInputError(input);
                    
                    // Additional validation based on input type
                    if (input.type === 'email' && !validateEmail(input.value)) {
                        isValid = false;
                        showInputError(input, 'Please enter a valid email address');
                    }
                    
                    // Password validation
                    if (input.name === 'password1' && input.value.length < 8) {
                        isValid = false;
                        showInputError(input, 'Password must be at least 8 characters');
                    }
                    
                    // Password confirmation validation
                    if (input.name === 'password2') {
                        const password1 = form.querySelector('input[name="password1"]');
                        if (password1 && input.value !== password1.value) {
                            isValid = false;
                            showInputError(input, 'Passwords do not match');
                        }
                    }
                }
            });
            
            // Prevent form submission if validation fails
            if (!isValid) {
                event.preventDefault();
            }
        });
    });
}

// Function to validate email format
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Function to show input error
function showInputError(input, message) {
    // Clear any existing error
    clearInputError(input);
    
    // Create error element
    const errorElement = document.createElement('div');
    errorElement.className = 'input-error';
    errorElement.textContent = message;
    
    // Add error styling to input
    input.classList.add('input-error-border');
    
    // Insert error after input's parent (the input-with-icon div)
    input.parentElement.insertAdjacentElement('afterend', errorElement);
}

// Function to clear input error
function clearInputError(input) {
    // Remove error styling
    input.classList.remove('input-error-border');
    
    // Remove error message if it exists
    const errorElement = input.parentElement.parentElement.querySelector('.input-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// Function to initialize input focus effects
function initInputEffects() {
    const inputs = document.querySelectorAll('.input-with-icon input');
    
    inputs.forEach(input => {
        // Add focus effect
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focus');
            const icon = this.parentElement.querySelector('i');
            if (icon) {
                icon.classList.add('icon-focus');
            }
        });
        
        // Remove focus effect
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focus');
            const icon = this.parentElement.querySelector('i');
            if (icon) {
                icon.classList.remove('icon-focus');
            }
        });
    });
}

// Function to initialize profile page animations
function initProfileAnimations() {
    // Animate stats numbers counting up
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(stat => {
        const finalValue = parseInt(stat.textContent);
        if (!isNaN(finalValue)) {
            animateCounter(stat, 0, finalValue, 1500);
        }
    });
    
    // Add hover effects to prediction items
    const predictionItems = document.querySelectorAll('.prediction-item');
    
    predictionItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
}

// Function to animate counter
function animateCounter(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        
        // Add % sign if the original text had it
        if (element.textContent.includes('%')) {
            element.textContent = `${value}%`;
        } else {
            element.textContent = value;
        }
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}