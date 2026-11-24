/**
 * Tech Mart - Interactive Client Script
 */

document.addEventListener('DOMContentLoaded', function () {
    // Pincode Delivery Estimator
    const pincodeBtn = document.getElementById('btn-check-pincode');
    const pincodeInput = document.getElementById('input-pincode');
    const pincodeResult = document.getElementById('pincode-result');

    if (pincodeBtn && pincodeInput && pincodeResult) {
        pincodeBtn.addEventListener('click', function () {
            const pin = pincodeInput.value.trim();
            if (pin.length !== 6 || isNaN(pin)) {
                pincodeResult.innerHTML = '<span class="text-danger small"><span class="material-symbols-outlined align-middle fs-6">error</span> Please enter a valid 6-digit Indian PIN code.</span>';
                return;
            }

            pincodeResult.innerHTML = '<span class="text-muted small"><span class="spinner-border spinner-border-sm me-1"></span> Checking serviceability...</span>';

            fetch(`/api/check-pincode/?pincode=${pin}`)
                .then(response => response.json())
                .then(data => {
                    if (data.valid) {
                        pincodeResult.innerHTML = `
                            <div class="d-flex align-items-center gap-2 p-2 rounded bg-success-subtle text-success-emphasis border border-success-subtle mt-2">
                                <span class="material-symbols-outlined fs-5">check_circle</span>
                                <div class="small">
                                    <strong>Express Delivery to ${data.city} (${data.pincode}):</strong>
                                    <div>Get it by <strong>${data.estimated_date}</strong> with Priority Air. COD available.</div>
                                </div>
                            </div>
                        `;
                    } else {
                        pincodeResult.innerHTML = `<span class="text-danger small">${data.message}</span>`;
                    }
                })
                .catch(() => {
                    pincodeResult.innerHTML = '<span class="text-danger small">Could not check pincode. Please try again.</span>';
                });
        });
    }

    // Smooth Category Scroll Navigation (Home Shelf)
    const catShelf = document.getElementById('tm-category-shelf');
    const catLeft = document.getElementById('cat-scroll-left');
    const catRight = document.getElementById('cat-scroll-right');
    if (catShelf && catLeft && catRight) {
        catLeft.addEventListener('click', function () {
            catShelf.scrollBy({ left: -320, behavior: 'smooth' });
        });
        catRight.addEventListener('click', function () {
            catShelf.scrollBy({ left: 320, behavior: 'smooth' });
        });
    }

    // Header Category Sub-Navigation Scroll & Mouse Wheel
    const navCatScroll = document.getElementById('tm-cat-nav-scroll');
    const navCatLeft = document.getElementById('tm-cat-scroll-left');
    const navCatRight = document.getElementById('tm-cat-scroll-right');
    if (navCatScroll) {
        if (navCatLeft) {
            navCatLeft.addEventListener('click', function () {
                navCatScroll.scrollBy({ left: -260, behavior: 'smooth' });
            });
        }
        if (navCatRight) {
            navCatRight.addEventListener('click', function () {
                navCatScroll.scrollBy({ left: 260, behavior: 'smooth' });
            });
        }
        navCatScroll.addEventListener('wheel', function (e) {
            if (e.deltaY !== 0) {
                e.preventDefault();
                navCatScroll.scrollLeft += e.deltaY * 1.5;
            }
        }, { passive: false });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
});
