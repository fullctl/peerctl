(function($, $tc, $ctl) {

$ctl.application.Peerctl.PeerGroups = $tc.extend(
  "PeerGroups",
  {
    PeerGroups : function() {
      this.Tool("peering_peer-groups");
    },

    init : function() {
      this.delete_selected_button = this.$t.button_delete_selected;

      this.widget("list", ($e) => {
        return new $ctl.widget.SelectionList(
          this.template("list", this.$e.body),
          $(this.delete_selected_button)
        );
      });

      this.delete_selected_button.on("click", () => {
        this.$w.list.delete_selected_list("slug");
      });

      this.$w.list.formatters.row = (row, data) => {
        row.find("[data-action=edit_peer_group]").click(() => {
          const modal = new $ctl.application.Peerctl.ModalPeerGroup();
          const form = modal.form;
          form.form_action = data.slug;
          form.method = "PUT";
          title = "Edit Peer Group";
          form.fill(data);
        });
      }

      $(this.$w.list).on("api-write:success", (ev, e, payload, response) => {
        fullctl.peerctl.$t.policies.$w.form.peer_group_select.load();
      });
      
    },

    menu : function() {
      this.Tool_menu();
      this.$e.menu.find('[data-element="button_add_peer_group"]').click(() => {
        new $ctl.application.Peerctl.ModalPeerGroup();
      });

      $(this.delete_selected_button).insertBefore(this.$e.menu.find('[data-element="button_add_peer_group"]'));
    },

    sync : function() {
      this.$w.list.load();
    }

  },
  $ctl.application.Tool
);

$ctl.application.Peerctl.ModalPeerGroup = $tc.extend(
  "ModalPeerGroup",
  {
    ModalPeerGroup : function(facility, device, port, session) {
      const modal = this;
      const form = this.form = new twentyc.rest.Form(
        $ctl.template("form_peer_group")
      );
      const title = "Add peer group"

      $(this.form).on("api-write:success", (ev, e, payload, response) => {
        modal.hide();
        fullctl.peerctl.$t.peer_groups.sync();
        fullctl.peerctl.$t.policies.$w.form.peer_group_select.load();
      });
      
      this.form.element.find('[data-bs-toggle="tooltip"]').tooltip();
      this.Modal("save_right", title, form.element);
      form.wire_submit(this.$e.button_submit);
    }
  },
  $ctl.application.Modal
);

$ctl.application.Peerctl.SummaryPeerSessionPolicySelect = $tc.extend(
  "SummaryPeerSessionPolicySelect",
  {
    SummaryPeerSessionPolicySelect : function(jq) {
      this.SimpleSelect2(jq);
      jq.select2({
        dropdownParent: jq.parent()
      });
      // fixing not being able to scroll modal when select2 opened
      $(jq).on('select2:open', function (e) {
        const evt = "scroll.select2";
        $(e.target).parents().off(evt);
        $(window).off(evt);
      });
    },
  },
  fullctl.ext.SimpleSelect2
)

$($ctl).on("init_tools", (e, app) => {
  // init sessions summary tool
  app.tool("peer_groups", () => {
    return new $ctl.application.Peerctl.PeerGroups();
  });

  app.$t.peer_groups.activate();
  app.$t.peer_groups.sync();
});

})(jQuery, twentyc.cls, fullctl);