(function($, $tc, $ctl) {

$ctl.application.Peerctl.SessionsSummary = $tc.extend(
  "SessionsSummary",
  {
    SessionsSummary : function() {
      this.Tool("peering_summary-sessions");

      this.ports = {};
      this.filters = [];

      this.widget("select_port", ($e) => {
        return this.setup_select_filter('#page-summary-sessions select[data-element="select_port"]');
      });

      this.widget("select_device", ($e) => {
        return this.setup_select_filter('#page-summary-sessions select[data-element="select_device"]');
      });

      this.widget("select_facility", ($e) => {
        return this.setup_select_filter('#page-summary-sessions select[data-element="select_facility"]');
      });

      this.widget("btn_add_peer_session", ($e) => {
        return $('#page-summary-sessions button[data-element="btn_add_peer_session"]');
      });

      this.widget("searchbar", ($e) => {
        return new fullctl.application.Searchbar(
          $('#page-summary-sessions [data-element="summary_searchbar"]'),
          () => this.sync(),
          () => this.sync()
        );
      });

      this.$w.select_port.format_request_url = (url) => {
        let device_filter = this.$w.select_device.element.val();
        if(device_filter != "all") {
          url = url + "?device="+device_filter;
        }
        return url;
      };

      this.$w.select_device.format_request_url = (url) => {
        return url.replace(/fac_tag/g, this.$w.select_facility.element.val());
      };

      this.$w.btn_add_peer_session.click(() => {
        new $ctl.application.Peerctl.ModalFloatingSession(
          this.$w.select_facility.element.val(),
          this.$w.select_device.element.val(),
          this.$w.select_port.element.val(),
        );
      });

      // set up delete selected button
      this.delete_selected_button = this.$t.button_delete_selected;
      $(this.delete_selected_button).insertBefore(this.$w.btn_add_peer_session);

      // setup session summary widget
      this.widget("list_peer_sessions", ($e) => {
        let w = new $ctl.widget.SelectionList(
          $('#summary-sessions-body table'),
          $(this.delete_selected_button)
        );

        w.formatters.row = (row, data) => {
          // add network tooltip to asn
          const asn_field = row.find('[data-field="peer_asn"]');
          asn_field.attr("data-bs-toggle", "tooltip")
            .attr("data-bs-placement", "top")
            .attr("title", data.peer_name)
            .addClass("dotted-underline");
          new bootstrap.Tooltip(asn_field);

          // add ip tooltip to ip container
          const ip_container = row.find('[data-element="ip_container"]');
          ip_container.attr("data-bs-toggle", "tooltip")
            .attr("data-bs-placement", "top")
            .attr("title", `${data.ip4}\n${data.ip6}`)
            .addClass("dotted-underline");
          new bootstrap.Tooltip(ip_container);

          // add class to row based on peer type
          row.attr("data-peer-session-type", data.peer_session_type);

          // handle policy editor widgets for each row
          row.find("[data-action=edit_session]").click(() => {
            new $ctl.application.Peerctl.ModalFloatingSession(null, null, null, data);
          });
        }

        w.formatters.meta4 = (value) => {
          if(!value)
            return "-";

          const node = $('<div class="d-flex align-items-center">');
          if (value.session_state && value.session_state == "ESTABLISHED") {
            node.append($('<span class="icon icon-triangle-fill-up me-auto">'))
            node.addClass("up")
          } else {
            node.append($('<span class="icon icon-triangle-fill-down me-auto">'))
            node.addClass("down")
          }

          value.last_updown = value.last_updown ? fullctl.formatters.seconds_to_wdhms(value.last_updown) : '-';
          node.append($('<span class="ps-1">').text(
            (value.accepted ? fullctl.formatters.shorten_number(value.accepted) : '0') +
            "/" +
            (value.received ? fullctl.formatters.shorten_number(value.received) : '0')
          ));
          node.append($('<span data-bs-html="true" data-bs-toggle="tooltip" data-bs-placement="top">').prop("title", fullctl.formatters.meta_data(value).html()).tooltip().append(
            $('<span class="icon fullctl icon-list">')
          ));

          return node;

        };

        w.formatters.meta6 = w.formatters.meta4;

        return w;
      });

      this.widget("no_port_assigned_filter_button", ($e) => {
        return new $ctl.application.Peerctl.NoPortAssignedFilterButton(
          $('#page-summary-sessions [data-element="filter_no_port_assigned"]'),
          this.$w.list_peer_sessions
        );
      });


      this.widget("count_panel", ($e) => {
        return new $ctl.application.Peerctl.SummaryCountsPanel(this.$w.list_peer_sessions);
      });

      // set up delete select functionality
      $(this.delete_selected_button).click(() => {
        if (confirm("Remove selected Peer Sessions?")) {
          this.$w.list_peer_sessions.delete_selected_list();
        }
      });

      // determine autoloading of filter arguments
      const autoload = this.autoload = $ctl.peerctl.autoload_enabled(
        "page-summary-sessions",
        (v) => { return (v && v != "all"); },
        ["facility", "device", "port", "peer"]
      );

      // wire initial setting of filter values if autoload is enabled
      if(autoload && autoload.facility) {
        $(this.$w.select_facility).one("load:after", () => {
          this.$w.select_facility.element.val(autoload.facility);
          this.toggle_facility_filters();
          this.update_filter_localstorage();
        });
      }

      if(autoload && autoload.device) {
        $(this.$w.select_device).one("load:after", () => {
          this.$w.select_device.element.val(autoload.device);
          this.toggle_device_filters();
          this.update_filter_localstorage();
        });
      }

      if(autoload && autoload.port) {
        $(this.$w.select_port).one("load:after", () => {
          this.$w.select_port.element.val(autoload.port);
          this.update_filter_localstorage();
        });
      }

      if (autoload && autoload.peer) {
        this.$w.searchbar.element.val(autoload.peer);
        this.$w.searchbar.show_clear_button();
      }

      // set-up localstorage sync for filters
      this.$w.select_port.init_localstorage();
      this.$w.select_device.init_localstorage();
      this.$w.select_facility.init_localstorage();


      $(this.$w.select_port.element).on("change", () => {
        this.update_filter_localstorage();
        this.sync();
      });
      $(this.$w.select_device.element).on("change", () => {
        this.toggle_device_filters();
        this.update_filter_localstorage();
        this.sync();
      });
      $(this.$w.select_facility.element).on("change", () => {
        this.toggle_facility_filters();
        this.update_filter_localstorage();
        this.sync();
      });

      // if autoloading of filters is enabled, sync the session list from
      // the filters provided in the autoload arguments

      if(autoload) {
        this.sync(
          autoload.facility,
          autoload.device,
          autoload.port,
          autoload.peer
        );
        this.$w.select_facility.load().then(() => this.sync);
      } else {
        // load filters from localstorage if available
        this.$w.select_facility.load().then(() => {
          if(this.$w.select_device.localstorage_get()) {
            $(this.$w.select_device).one("load:after", () => {
              $(this.$w.select_port).one("load:after", () => {
                this.sync();
              })
              this.toggle_device_filters();
            });
            this.toggle_facility_filters();
          } else {
            this.$w.select_facility.element.val();
            this.sync();
          }
        });
      }
    },

    /**
     * This will show and load the port filter if a device is selected
     * otherwise it will hide the port filter.this
     *
     * @method toggle_device_filters
     */

    toggle_device_filters : function() {
      this.$w.select_port.element.empty();

      if(!this.$w.select_device.element.val() || this.$w.select_device.element.val() == "all") {
        this.$w.select_port.element.parents('.toolbar-control-group').hide();
      } else {
        this.$w.select_port.element.parents('.toolbar-control-group').show();
        this.$w.select_port.load()
      }
    },

    /**
     * This will show and load the device filter if a facility is selected
     * otherwise it will hide the device and the port filter.
     *
     * @method toggle_facility_filters
     */

    toggle_facility_filters : function() {
      this.$w.select_device.element.empty();

      if(this.$w.select_facility.element.val() == "all") {
        this.$w.select_device.element.parents('.toolbar-control-group').hide();
      } else {
        this.$w.select_device.element.parents('.toolbar-control-group').show();
        this.$w.select_device.load()
      }
      this.toggle_device_filters();
    },

    /**
     * This will update the localstorage values for the filters.
     *
     * @method update_filter_localstorage
     */

    update_filter_localstorage: function() {
      const select_device = this.$w.select_device;
      const select_facility = this.$w.select_facility;
      const select_port = this.$w.select_port;

      const default_value = "all";

      const select_device_val = select_device.element.val();
      if (select_device_val == default_value || select_device_val === null) {
        select_device.localstorage_remove()
      } else {
        select_device.localstorage_set(select_device_val)
      }

      const select_facility_val = select_facility.element.val();
      if (select_facility_val == default_value || select_facility_val === null) {
        select_facility.localstorage_remove()
      } else {
        select_facility.localstorage_set(select_facility_val)
      }

      const select_port_val = select_port.element.val();
      if (select_port_val == default_value || select_port_val === null) {
        select_port.localstorage_remove()
      } else {
        select_port.localstorage_set(select_port_val)
      }
    },

    /**
     * Updates the # parameter in the url for autoloading
     *
     * filter arguments
     * @method sync_url
     * @param {Boolean} force if true will also update the url if the session summary is currently not visible
     * @param {String} facility facility slug
     * @param {Number} device device id
     * @param {Number} port port id
     * @param {String} q peer asn, name or ip
     */

    sync_url: function(force, facility, device, port, q) {
      if(this.$w.select_facility.element.is(":visible") || force) {
        window.history.pushState({}, '', "#page-summary-sessions;"+(facility||'')+";"+(device||'')+";"+(port||"")+";"+(q||""));
      }
    },

    /**
     * Syncs the session list from the api according to the specified
     * filter arguments
     *
     * If not filter arguments are provided, filters will be read from the
     * filter input elements.
     *
     * @method sync
     * @param {String} facility_filter facility slug
     * @param {Number} device_filter device id
     * @param {Number} port_filter port id
     * @param {String} peer_filter peer asn, name or ip
     */

    sync: function(facility_filter, device_filter, port_filter, peer_filter) {
      // if no filters were provided to the function read the filter values
      // from the various filter elements

      if(!facility_filter && !device_filter && !port_filter && !peer_filter) {
        port_filter = this.$w.select_port.element.val();
        device_filter = this.$w.select_device.element.val();
        facility_filter = this.$w.select_facility.element.val();
        peer_filter = this.$w.searchbar.element.val();
      }

      if(peer_filter && !facility_filter) {
        facility_filter = "all";
      }

      this.$w.list_peer_sessions.action = "";

      // update the url with filter values

      this.sync_url(false, facility_filter, device_filter, port_filter, peer_filter);

      // build the request path from the filters

      var action = "";

      if(port_filter && !isNaN(port_filter)) {
        action = "port/"+port_filter;
      } else if(device_filter && !isNaN(device_filter)) {
        action = "device/"+device_filter;
      } else if(facility_filter != "all") {
        action = "facility/"+facility_filter;
      }

      this.$w.list_peer_sessions.payload = function() {
        if(peer_filter && peer_filter != "") {
          return {peer:peer_filter}
        }
        return {};
      }

      // update list
      this.$w.list_peer_sessions.action = action;

      const load_list = () => {
        this.syncing = true;
        this.$w.list_peer_sessions.load().finally(() => {
          this.syncing = false;
        });
      }
      // if list is already loading, wait fot it to finish
      // and then reload the list to prevent overwriting
      if(this.syncing) {
        // remove any existing pending
        $(this.$w.list_peer_sessions).off("load:after", load_list);
        // resync with new data after the current sync is finished
        $(this.$w.list_peer_sessions).one("load:after", load_list);

        return;
      }

      load_list();

      // update API view link

      this.$e.btn_api_view.attr("href", this.$w.list_peer_sessions.base_url+"/"+this.$w.list_peer_sessions.action);

    },

    setup_select_filter : function(selector) {
      let jq = $(selector);
      var w = new twentyc.rest.Select(jq);
      $(w).on("load:after", (event, element, data) => {
        var i;
        for(i = 0; i < data.length; i++) {
          this.ports[data[i].id] = data[i];
        }
        if(data.length == 0) {
          jq.attr('disabled', true);
        } else {
          jq.attr('disabled', false)
        }
      });


      this.filters.push(w)
      return w
    },

    clear_select_filter : function() {
      for (let i = 0; i < this.filters.length; i++) {
        this.filters[i].val('all');
      }
      this.toggle_facility_filters();
      this.update_filter_localstorage();
    }
  },
  $ctl.application.Tool
);

$ctl.application.Peerctl.SummaryCountsPanel = $tc.extend(
  "CountsPanel",
  {
    CountsPanel : function(list) {
      this.Component("summary-counts-panel");
      this.list = list;

      this.widget("ixp_btn", ($e) => {
        return new $ctl.application.Peerctl.CountsButton(this.$e.ixp_btn, this.list);
      });

      this.widget("pni_btn", ($e) => {
        return new $ctl.application.Peerctl.CountsButton(this.$e.pni_btn, this.list);
      });

      this.widget("transit_btn", ($e) => {
        return new $ctl.application.Peerctl.CountsButton(this.$e.transit_btn, this.list);
      });

      this.widget("customer_btn", ($e) => {
        return new $ctl.application.Peerctl.CountsButton(this.$e.customer_btn, this.list);
      });

      this.widget("core_btn", ($e) => {
        return new $ctl.application.Peerctl.CountsButton(this.$e.core_btn, this.list);
      });

      $(this.list).on("load:after", () => {this.update()});
    },

    update : function() {
      const rows = this.get_list_rows();
      this.$e.total.text(rows.length);
      this.$w.ixp_btn.text(this.get_list_rows("ixp").length);
      this.$w.pni_btn.text(this.get_list_rows("pni").length);
      this.$w.transit_btn.text(this.get_list_rows("transit").length);
      this.$w.customer_btn.text(this.get_list_rows("customer").length);
      this.$w.core_btn.text(this.get_list_rows("core").length);

      const unique_counts = this.get_unique_asn_session_type_counts();
      this.$e.unique_ixp_count.find('.value').text(unique_counts.ixp);
      this.$e.unique_pni_count.find('.value').text(unique_counts.pni);
      this.$e.unique_transit_count.find('.value').text(unique_counts.transit);
      this.$e.unique_customer_count.find('.value').text(unique_counts.customer);
    },

    /**
     * Returns a jquery object containing the rows of the list
     *
     * @param {String} type peer session type
     * @returns
     */
    get_list_rows : function(type) {
      const rows = this.list.list_body.find('tr');
      if (type)
        return rows.filter('tr[data-peer-session-type="'+type+'"]');
      return rows;
    },

    get_unique_asn_session_type_counts : function() {
      const asn_dict = {
        ixp: new Set(),
        pni: new Set(),
        transit: new Set(),
        customer: new Set(),
        core: new Set()
      };

      this.list.list_body.find('tr').each(function() {
        const session = $(this).data('apiobject');
        if (asn_dict[session.peer_session_type]) {
          asn_dict[session.peer_session_type].add(session.peer_asn);
        }
      })

      return {
        ixp: asn_dict.ixp.size,
        pni: asn_dict.pni.size,
        transit: asn_dict.transit.size,
        customer: asn_dict.customer.size,
        core: asn_dict.core.size
      }
    }
  },
  $ctl.application.Component
);

$ctl.application.Peerctl.CountsButton = $tc.define(
  "CountsButton",
  {
    CountsButton : function(jq, list) {
      const element = this.element = jq;
      this.element.find(".filter-btn").on("click", function() {
        this.classList.toggle("active");
        this.classList.toggle("inactive");
        list.list_body.toggleClass("filter-out-" + element.data('element'));
      });
    },

    text : function(text) {
      this.element.find('.value').text(text);
    }
  },
);

$ctl.application.Peerctl.NoPortAssignedFilterButton = $tc.define(
  "NoPortAssignedFilterButton",
  {
    NoPortAssignedFilterButton : function(jq, list) {
      this.element = jq;
      this.list = list;
      this.filter_active = false;

      $(this.list).on("load:after", () => {
        this.update_count();
      });

      this.element.click(() => {
        this.toggle_no_port_assigned_filter();
      });
    },

    _is_no_port_assigned : function(session) {
      return session.port_id == 0;
    },

    update_count : function() {
      const count_element = this.element.find('.value');

      const widget = this;
      let sessions_no_port_assigned = 0;
      this.list.list_body.find("tr").each(function() {
        const data = $(this).data("apiobject");
        if (widget._is_no_port_assigned(data)) {
          sessions_no_port_assigned++;
        }
      });

      count_element.text(sessions_no_port_assigned);
    },

    /**
     * Add a class to rows that do not have a aport assigned. This is used to
     * hide them.
     *
     * @method hide_port_assigned_session
     * @param {Event} e
     * @param {jQuery} row
     * @param {Object} data
     */
    hide_port_assigned_session : function(e, row, data) {
      if (!this._is_no_port_assigned(data)) {
        row.addClass('filter-no-port-hidden');
      } else {
        row.removeClass('filter-no-port-hidden');
      }
    },

    /**
     * hides or shows sessions with no port assigned in the list.
     *
     * @method toggle_non_active_filter
     * @param {Boolean} [active]
     */
    toggle_no_port_assigned_filter : function(active = null) {
      this.filter_active = active != null ? active : !this.filter_active;
      this.element.toggleClass("active", this.filter_active);

      // make _is_no_port_assigned available to the list
      this.list._is_no_port_assigned = this._is_no_port_assigned;
      if (this.filter_active) {
        $(this.list).on("insert:after", this.hide_port_assigned_session)
      } else {
        $(this.list).off("insert:after", this.hide_port_assigned_session)
      }

      this.list.load();
    },
  }
);

$ctl.application.Peerctl.ModalFloatingSession = $tc.extend(
  "ModalFloatingSession",
  {
    ModalFloatingSession : function(facility, device, port, session) {
      const modal = this;
      const form = this.form = new twentyc.rest.Form(
        $ctl.template("form_floating_session")
      );
      var title = "Add peer session"

      this.session = session;

      this.select_port = this.form.element.find('#port');
      this.select_policy_4 = new twentyc.rest.Select(this.form.element.find('#policy-4'));
      this.select_policy_6 = new twentyc.rest.Select(this.form.element.find('#policy-6'));

      if(port == "all")
        port = null;

      // setup port auto complete

      fullctl.ext.select2.init_autocomplete(

        // bind to port <select> element
        form.element.find("#port"),

        // parent dropdown to form element
        form.element,

        // options
        {

          // autocomplete url
          url: "/autocomplete/device/port?org="+fullctl.org.slug,

          // process results, allowing us to add entries for
          // ips that are not assigned to a port
          process: (data, term, params) => {
            if(fullctl.util.is_valid_ip4(term)) {

              // check if we have an exact match for the ip in the results
              var exact_found = data.results.find((obj) => {
                return obj.text.primary && obj.text.primary.split("/")[0] == term
              });

              if(!exact_found) {

                // if no exact match was found, add an entry for the ip that
                // can be selected as a choice.

                data.results.unshift({
                  id: term,
                  text: {primary: term, secondary:"Ip not assigned", extra:""},
                  selected_text: {primary: term, secondary:"Ip not assigned", extra:""}
                });
              }
            }
          },

          // place holder text for the search field
          placeholder: "Search IP, device, port or location names.",

          // if session is specifed, preselect it's port
          initial: (
            session ?
            {
              id: session.port_id,
              primary: session.ip4,
              secondary: session.port_interface,
              extra: session.device_name
            }
            : null
          )
        }
      );

      // edit existing session

      if(session) {
        title = "Edit Session ["+session.id+"]";
        form.fill(session);
        port = session.port_id;
      }

      this.preselect_port = port;

      this.select_policy_4.load(session ? session.policy4_id : null);
      this.select_policy_6.load(session ? session.policy6_id : null);

      $(this.form).on("api-write:success", (ev, e, payload, response) => {
        modal.hide();
        fullctl.peerctl.$t.sessions_summary.$w.list_peer_sessions.load();
      });

      // scroll to errors becaues form is long
      const post_failure_orig = form.post_failure.bind(form);
      form.post_failure = (response) => {
        post_failure_orig(response);
        $(form.element).find(".validation-error").first().each(function() {
          this.scrollIntoView({behavior: "smooth"});
        })
      }

      this.Modal("save_right", title, form.element);
      form.wire_submit(this.$e.button_submit);
    }
  },
  $ctl.application.Modal
);

$($ctl).on("init_tools", (e, app) => {
  // init sessions summary tool
  app.tool("sessions_summary", () => {
    return new $ctl.application.Peerctl.SessionsSummary();
  });

  app.$t.sessions_summary.activate();

  $('#tab-summary-sessions').on('show.bs.tab', () => {
    // get filter values
    const port_filter = app.$t.sessions_summary.$w.select_port.element.val();
    const device_filter = app.$t.sessions_summary.$w.select_device.element.val();
    let facility_filter = app.$t.sessions_summary.$w.select_facility.element.val();
    const peer_filter = app.$t.sessions_summary.$w.searchbar.element.val();

    if(peer_filter && !facility_filter) {
      facility_filter = "all";
    }

    // update the url with filter values
    app.$t.sessions_summary.sync_url(true, facility_filter, device_filter, port_filter, peer_filter);
  });

});

})(jQuery, twentyc.cls, fullctl);