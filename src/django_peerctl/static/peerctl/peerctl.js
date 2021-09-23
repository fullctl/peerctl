(function($, $tc, $ctl) {

$ctl.application.Peerctl = $tc.extend(
  "Peerctl",
  {
    Peerctl: function() {
      this.Application("peerctl");
    }
  },
  $ctl.application.Application
);

$(document).ready(function() {
  $ctl.peerctl = new $ctl.application.Peerctl();
});

})(jQuery, twentyc.cls, fullctl);
