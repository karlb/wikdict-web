function show_translation(event) {
  event.preventDefault();

  const clicked_text = this;
  const translate_id = this.dataset.translate;
  this.setAttribute('data-current', '');
  const tooltip = document.querySelector('#' + translate_id);
  tooltip.setAttribute('data-show', '');
  const popper = Popper.createPopper(this, tooltip, {
    modifiers: [
      {
        name: 'offset',
        options: {
          offset: [0, 8],
        },
      },
    ],
  }
  );
  document.body.addEventListener('click', function() {
    tooltip.removeAttribute('data-show');
    clicked_text.removeAttribute('data-current');
  }, { capture: true, once: true });
}

const nodes = document.querySelectorAll('[data-translate]');
nodes.forEach(node => {
  node.addEventListener('click', show_translation, false);
})

