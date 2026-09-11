// Home page animations and interactions for FutureCoin

document.addEventListener('DOMContentLoaded', function() {
    // Initialize floating coins animation with random movements
    initFloatingCoins();
    
    // Add hover effects to feature cards
    initFeatureCards();
});

// Function to initialize the floating cryptocurrency coins with random movements
function initFloatingCoins() {
    const coins = document.querySelectorAll('.coin');
    
    coins.forEach(coin => {
        // Add random initial position variations
        const randomX = Math.random() * 10 - 5;
        const randomY = Math.random() * 10 - 5;
        const randomDelay = Math.random() * 2;
        const randomDuration = 8 + Math.random() * 4;
        
        coin.style.transform = `translate(${randomX}px, ${randomY}px)`;
        coin.style.animationDelay = `${randomDelay}s`;
        coin.style.animationDuration = `${randomDuration}s`;
        
        // Add click interaction to coins
        coin.addEventListener('click', function() {
            const coinType = this.getAttribute('data-coin');
            highlightCoin(this, coinType);
        });
    });
}

// Function to highlight a coin when clicked
function highlightCoin(coinElement, coinType) {
    // Remove highlight from all coins
    document.querySelectorAll('.coin').forEach(c => {
        c.classList.remove('highlighted');
    });
    
    // Add highlight to clicked coin
    coinElement.classList.add('highlighted');
    
    // Create a pulse effect
    const pulse = document.createElement('div');
    pulse.classList.add('coin-pulse');
    coinElement.appendChild(pulse);
    
    // Display coin info tooltip
    const tooltip = document.createElement('div');
    tooltip.classList.add('coin-tooltip');
    
    // Set tooltip content based on coin type
    let tooltipContent = '';
    switch(coinType) {
        case 'BTC':
            tooltipContent = 'Bitcoin (BTC) - The original cryptocurrency';
            break;
        case 'ETH':
            tooltipContent = 'Ethereum (ETH) - Smart contract platform';
            break;
        case 'BNB':
            tooltipContent = 'Binance Coin (BNB) - Binance exchange token';
            break;
        case 'DOGE':
            tooltipContent = 'Dogecoin (DOGE) - Started as a meme, now a top crypto';
            break;
    }
    
    tooltip.textContent = tooltipContent;
    coinElement.appendChild(tooltip);
    
    // Remove tooltip and pulse after animation
    setTimeout(() => {
        if (pulse.parentNode === coinElement) {
            coinElement.removeChild(pulse);
        }
        if (tooltip.parentNode === coinElement) {
            coinElement.removeChild(tooltip);
        }
    }, 3000);
}

// Function to initialize feature cards with hover effects
function initFeatureCards() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('card-hover');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('card-hover');
        });
    });
}