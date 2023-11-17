(function($, $tc, $ctl) {

$ctl.application.Peerctl.Networks = $tc.extend(
  "Networks",
  {

    Networks : function() {
      this.Tool("networks");
    },

    init : function() {
      this.widget("list", ($e) => {
        return new twentyc.rest.List(
          this.template("list", this.$e.body)
        );
      })

      this.$w.list.format_request_url = (url) => {
        return url.replace(/other_asn/, this.select_network_search.val());
      }

      $(this.$w.list).on("api-read:success", (ev, endpoint, payload, response) => {

        if(!response.first()) {
          $('#network-search-result-name').text("");
          $('#network-search-result-asn').text("");
          this.peer = null;
          $('#searched-asn').text("");
          return;
        }

        this.peer = response.first();

        $('#network-search-result-name').text(this.peer.name);
        $('#network-search-result-asn').text(this.peer.asn);
        $('#searched-asn').text(this.peer.asn);

        this.peer_request_data = {type: "email"}
        // autopeer
        let url = `/api/autopeer/${fullctl.peerctl.network.asn}/enabled/${this.peer.asn}/`

        $.ajax({
          url: url,
          method: "GET",
          headers : {
            "Content-Type" : "application/json",
            "X-CSRFToken" : twentyc.rest.config.csrf
          },
        }).then((response)=>{
          const autopeer_data = this.autopeer_data = response.data[0];
          if (autopeer_data.enabled) {
            const autopeer_btn = $(`
                <button
                  class="primary btn | small active"
                  data-option-text="Autopeer"
                >
                  <div class="row align-items-center">
                    <div class="col label pe-0">
                      Request peering
                    </div>
                    <div class="col-auto">
                      <span class="icon icon-api"></span>
                    </div>
                  </div>
                </button>
            `)
            this.request_peering_btn.add_option(autopeer_btn);
            autopeer_btn.click(()=>{
              this.peer_request_data = {type: "autopeering", url: this.autopeer_data.url, autopeer_enabled: true, asn: this.peer.asn},
              this.request_peering();
            });

            this.$w.list.list_body.find('[data-element="request_peering"]').off('click')
            this.$w.list.element.find('[data-element="request_peering"]').on('click', ()=>{
              this.peer_request_data = {type: "email", url: this.autopeer_data.url, autopeer_enabled: true, asn: this.peer.asn};
              this.request_peering();
            });
          }
        });
      });

      this.$w.list.formatters.row = (row, data) => {
        row.data("ix-id", data.ix_id);

        const cont_us = $('<div>');
        const cont_them = $('<div>');
        const cont_mutual = $('<div>');
        const session_icon = $('<img>').attr('src', fullctl.util.static('common/icons/Indicator/Check-Ind/Check.svg')).addClass("indicator").attr("title", "Peering session(s) configured")
        let loc,i, node;


        for(i=0; i< data.our_locations.length; i++) {
          loc = data.our_locations[i];
          $('<div class="compact-row">').data("ix-id", loc.ix_id).append(
            $('<input type="checkbox">')
          ).append(
            $('<span>').text(loc.ix_name)
          ).appendTo(cont_us);
        }

        for(i=0; i< data.their_locations.length; i++) {
          loc = data.their_locations[i];
          $('<div class="compact-row">').data("ix-id", loc.ix_id).append(
            $('<input type="checkbox">')
          ).append(
            $('<span>').text(loc.ix_name)
          ).appendTo(cont_them);
        }

        for(i=0; i< data.mutual_locations.length; i++) {
          loc = data.mutual_locations[i];
          node = $('<div class="compact-row field">').data("ix-id", loc.ix_id).append(
            $('<input type="checkbox">')
          ).append(
            $('<span>').text(loc.ix_name).addClass((loc.session ? "session-active" : ""))
          ).appendTo(cont_mutual);

          if(loc.session) {
            node.append(session_icon.clone());
          }
        }

        row.find('.our-locations').append(cont_us);
        row.find('.their-locations').append(cont_them);
        row.find('.mutual-locations').append(cont_mutual);
      }

      $(this.$w.list).on("load:after", (ev,response) => {
        let request_peering = this.$w.list.element.find('[data-element=request_peering]');
        request_peering.show().prop("disabled", false).children('.label').hide().filter('.ok').show();

        let request_peering_tr = this.$w.list.element.find('[data-element=request_peering_tr]');

        this.$w.list.element.find('input[type=checkbox]:not(.select-all)').on("change", (ev) => {
          if(this.get_number_of_selected_networks() > 0) {
            request_peering.prop("disabled", false)
            request_peering_tr.show();
          } else {
            request_peering.prop("disabled", true)
            request_peering_tr.hide();
          }
        });

      });

      this.select_network_search = $ctl.peerctl.$c.toolbar.$e.network_search_asn;

      this.select_network_search.select2({
        ajax: {
          url : '/autocomplete/pdb/net',
          dataType: 'json',
          processResults : function(data, params) {

            var term = params.term;
            if(!isNaN(parseInt(term))) {
              var exact_found = data.results.find((obj) => { return obj.id == parseInt(term) });
              if(!exact_found) {
                data.results.unshift({
                  id: parseInt(term),
                  text: "AS"+term,
                  selected_text: "AS"+term
                });
              }
            }
            console.log("DATA", data.results, exact_found);
            return {
              results: data.results
            }
          }
        },
        placeholder: "Search by ASN"
      });

      this.select_network_search.on('select2:select', ()=> {
        this.sync();
      });

      $(document).on('select2:open', () => {
        document.querySelector('.select2-search__field').focus();
      });

      /*
      $(this.$w.list).on("load:after", () => {
        this.$e.request_peering.show();
      });

      this.input_network_search = $ctl.peerctl.$c.toolbar.$e.network_search;

      this.input_network_search.on("keydown", function(ev){
        if(ev.which == 13) {
          this.sync();
        }
      }.bind(this));

      this.btn_network_search = $ctl.peerctl.$c.toolbar.$e.network_search_submit;

      $(this.btn_network_search).click(function() {
        this.sync();
      }.bind(this));
      */

      this.$w.list.element.find("[data-element=request_peering]").on("click", () => {
        this.request_peering();
      });

      this.request_peering_btn = new fullctl.application.DropdownBtn(this.$w.list.element.find(".dropdown-btn"));

    },

    sync : function() {
      if(this.select_network_search.val())
        this.$w.list.load();
    },

    get_number_of_selected_networks() {
      return this.$w.list.element.find('input[type=checkbox]:checked').length;
    },

    request_peering : function(type) {

      if(!this.peer) {
        return alert("No network in results");
      }

      var selected = this.$w.list.element.find('input[type=checkbox]:checked').parent()
      var ix_ids = []

      selected.each(function() {
        ix_ids.push($(this).data("ix-id"));
      });

      new $peerctl.modals.RequestPeering(
        this.peer,
        this.peer_request_data,
        ix_ids,
      );
    }


  },
  $ctl.application.Tool
)

$($ctl).on("init_tools", (e, app) => {
  // init networks tool
  app.tool("networks", () => {
    return new $ctl.application.Peerctl.Networks();
  });

  app.$t.networks.activate();

  $('#tab-summary-sessions').on('show.bs.tab', () => {
  });

});

})(jQuery, twentyc.cls, fullctl);