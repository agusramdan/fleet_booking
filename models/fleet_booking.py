# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html
from email.policy import default

#from dev-addons.int_mceasy.models import fleet_vehicle_gps
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
#from dateutil.relativedelta import relativedelta

class FleetBooking(models.Model):
    _name = "fleet.booking"
    _description = "Fleet Booking Order for Logistic"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    #driver_id = fields.Many2one('res.partner', 'Driver',  help='Driver address of the vehicle', copy=False)
    
    # vehicle_id = fields.Many2one(
    #     comodel_name="fleet.vehicle",
    #     string="Vehicle",
    #     required=True,
    # )

    # master_route_id = fields.Many2one(
    #     comodel_name="route.planner",
    #     string="Route",
    # )
    
    multi_pickup = fields.Boolean("Multiple Pickup",default=False)
    multi_drop = fields.Boolean("Multiple Drop",default=False)
    multi_trip = fields.Boolean("Multiple Trip",default=False)

    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("approval", "Approval"),
            ("job", "Job Created"),
            ("done", "Done")
        ],
        default="open"
    )
    #
    # Origin di ambil dari waypoins index 0
    #
    origin_id = fields.Many2one(
        comodel_name="res.partner",
        string="Origin",
        required=False,
    )
    #
    # Destination di ambil dari waypoins index terakhir -1
    #

    destination_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination",
        required=False,
    )
    
    valid_booking = fields.Boolean()
    error_description = fields.Char()

    goods_ids = fields.One2many(
        comodel_name="fleet.booking.goods",
        inverse_name="booking_id",
        string="Package List",
    )

    issue_goods_ids = fields.One2many(
        comodel_name="fleet.booking.goods",
        inverse_name="booking_id",
        string="Route Issue",
        domain=[('route_issue', '=', 'True')], 
        readonly=True, 
        copy=False)

    waypoint_ids = fields.One2many(
        comodel_name="fleet.booking.waypoint", 
        inverse_name="booking_id",
        string="Waypoints",
    )
    
    waypoint_readonly_ids = fields.One2many(
        comodel_name="fleet.booking.waypoint", 
        inverse_name="booking_id",
        string="Waypoints/Stop Point",
        readonly=True
    )

    trip_ids = fields.One2many(
        comodel_name="fleet.booking.trip",
        inverse_name="booking_id",
        string="Trips",
    )
    @api.depends("multi_pickup","multi_drop")
    def _compute_multi_trip(self):
        for record in self:
            record.multi_trip = record.multi_pickup or record.multi_drop
    
         
    def _compute_multi_pickup(self):
        set_pickup = set()
        for record in self.goods_ids:
            set_pickup.add(record.pickup_id.id)
            # if record.pickup_id and record.pickup_id.id != self.origin_id.id :
            #     multi_pickup = True
            #     break
        
        self.multi_pickup = len(set_pickup)>1

    def _compute_multi_drop(self):
        set_drop = set()
        #multi_drop = False
        for record in self.goods_ids:
            set_drop.add(record.drop_id.id)
            # if record.drop_id and record.drop_id.id != self.destination_id.id :
            #     multi_drop = True
            #     break
        self.multi_drop= len(set_drop)>1


    route_status = fields.Selection(
        string='Route status',
        selection=[
            ("open", "Need Check"),
            ("package_change", "Package Change"),
            ("invalid_route", "Invalid Route"),
            ("valid_route", "Valid Route"),
        ],
        default="open"
    )

    def action_request_appoval(self):
        self.state="approval"


    def action_unlink_waypoints(self):
        self.action_unlink_trips() 
        self.waypoint_ids.unlink() 
        self.flush()

    def action_unlink_trips(self):
        self.trip_ids.unlink() 
        self.flush()

    def action_generate_waypoint(self):
        pickup_ids = []
        drop_ids = []
        new_waypoint = []
        for record in self.goods_ids :
            if record.pickup_id :
                pickup_id = record.pickup_id.id
                if pickup_id not in pickup_ids :  
                    pickup_ids.append(pickup_id)

            if record.drop_id :
                drop_id = record.drop_id.id
                if drop_id not in drop_ids :  
                    drop_ids.append(drop_id)

        for id in pickup_ids :
            if id not in new_waypoint :  
                    new_waypoint.append(id)
        for id in drop_ids :
            if id not in new_waypoint :  
                    new_waypoint.append(id)
        wp_ids= []
        sequence = -1
        for record in self.waypoint_ids :
            sequence = record.sequence 
            if record.waypoint_id :
                new_waypoint = [value for value in new_waypoint if value != record.waypoint_id.id ]
        
        for waypoint in new_waypoint :
            sequence = sequence + 1
            wp_ids.append((0,0,{'sequence':sequence,'waypoint_id': waypoint}))
            
        self.waypoint_ids=wp_ids

        self.action_validate_route()
    
    def action_validate_route(self):
        self._compute_multi_pickup()
        self._compute_multi_drop()
        self.flush()
        self._compute_multi_trip()
        self.route_status = "open"
        route_status="valid_route"
        origin_id = 0 
        waypoint_ids = []
        for wp in self.waypoint_ids :
            data = {
                    'id':wp.id,
                    'waypoint_id': wp.waypoint_id.id, 
                    'pickup_point': False,
                    'drop_point': False,
                }
            waypoint_ids.append(data)
    
         

        for record in self.goods_ids :
            pickup_id = record.pickup_id.id 
            # if record.pickup_id :
            #     pickup_id = record.pickup_id.id
            
            drop_id =  record.drop_id.id
            # if record.drop_id :
            #     drop_id = record.drop_id.id
            
            pickup_found = False
            drop_found = False
            
            for waypoint in waypoint_ids :
                if pickup_found and drop_found:
                    break
                waypoint_id = waypoint['waypoint_id']
                if not pickup_found :
                    pickup_found = pickup_id == waypoint_id
                    if pickup_found : waypoint['pickup_point']= True
                
                elif not drop_found :
                    drop_found = drop_id == waypoint_id
                    if drop_found : waypoint['drop_point']= True
            
            record.able_to_pickup=pickup_found
            record.able_to_deliver=drop_found
            if pickup_found and drop_found :
                record.route_issue = False
            else :  
                record.route_issue = True 
                route_status = "invalid_route"

        
        self.route_status = route_status
        self.flush()
        if route_status == 'valid_route' :
            """
                route valid update waypoint status
               (1, ID, { values })    update the linked record with id = ID (write *values* on it)
            
            """
            wp_ids= []
            for waypoint in waypoint_ids : 
                ID = waypoint['id']
                wp_ids.append((1,ID,{
                    'pickup_point':waypoint['pickup_point'],
                    'drop_point':waypoint['drop_point'],
                }))
                 
            self.waypoint_ids=wp_ids
            self.flush()

    def action_generate_trip(self):
        self.action_validate_route()
        if "valid_route" == self.route_status :
            trips = []
            last_waypoint = None
            sequence=0
            if self.waypoint_ids :
                for waypoint in self.waypoint_ids :                    
                    if last_waypoint :
                        trip = {
                            'sequence':sequence ,
                            'origin_id':last_waypoint.waypoint_id.id,
                            'wp_origin_id':last_waypoint.id ,                      
                            'destination_id':waypoint.waypoint_id.id,
                            'wp_destination_id':waypoint.id
                        }
                        sequence = sequence +1
                        trips.append((0,0,trip))  
                   
                    last_waypoint = waypoint

            self.trip_ids=trips
            self.flush()
            self._generate_trip_package()

    def _generate_trip_package(self):    
        """
        Trip per Package asumsi berurutan
        """
 
        booking_id = self.id
        for goods in self.goods_ids:
            """
                Iterasi setiap barang untuk di masukan pada trip
            """
            is_pickup = False
            is_origin_pickup = False
            if goods.pickup_id : is_origin_pickup = goods.pickup_id.id == self.origin_id.id
            else : is_origin_pickup = True
            is_destination_drop = False
            if goods.drop_id : is_destination_drop = goods.drop_id.id == self.destination_id.id
            else : is_destination_drop =  True

            for trip in self.trip_ids:
                """
                    Iterasi setiap barang untuk di masukan pada trip
                """
                is_curtrip_pickup = False
                is_curtrip_drop = False
                 
                if not is_pickup :
                    "Check pickup"
                    if trip.origin_id.id == goods.pickup_id.id :
                        "Chek"
                        is_curtrip_pickup=True
                        is_pickup = True
                if is_pickup :
                    "chek drop"
                    if trip.destination_id.id == goods.drop_id.id :
                        "Chek"
                        is_curtrip_drop=True
                
                    trip.goods_ids= [(0,0,{
                        'booking_id': booking_id,
                        'booking_goods_id': goods.id, 
                        'pickup_trip': is_curtrip_pickup,
                        'drop_trip': is_curtrip_drop,
                        'via_trip' : not (is_curtrip_pickup or is_curtrip_drop )
                    })]
                if is_curtrip_pickup: trip.pickup_trip = True
                if is_curtrip_drop : 
                    trip.drop_trip = True 
                    break

        self.flush()          
 

class FleetBookingGoods(models.Model):
    _name = "fleet.booking.goods"   
    _description = "Fleet Booking Order for packing list"  
    _order = "sequence, booking_id"

    sequence = fields.Integer()
    booking_id = fields.Many2one(
        comodel_name="fleet.booking",
        string="Booking",
        required=True,
    )
    # when null pickup is origin poi
    pickup_id = fields.Many2one(
        comodel_name="res.partner",
        string="Pickup",
        required=False
    )
    # when null drop point is destination poi
    drop_id = fields.Many2one(
        comodel_name="res.partner",
        string="Drop",
        required=False
    )

    dogs  = fields.Char('Description of Goods')

    # TODO ADD infomation dimension and weight 

    # Validate route
    able_to_pickup = fields.Boolean("Able to Pickup")
    able_to_deliver = fields.Boolean('Able to Deliver')
    route_issue = fields.Boolean('Shipment Issue')
    
    def add_waypoint(self):
        booking_id=self.booking_id
        lastseq = 0
        wp_ids= []
        after_insert_ids = []
        # sequence not generate proprely afer insert after
        if not self.able_to_pickup :
            wp_ids.append((0,0,{
                'sequence': 0,
                'waypoint_id': self.pickup_id.id, 
                'pickup_point': True, 
                }))
            lastseq =  lastseq + 1
            if not self.able_to_deliver :
                wp_ids.append((0,0,{
                    'sequence': lastseq,
                    'waypoint_id': self.drop_id.id, 
                    'drop_point': True,
                    }))
            lastseq =  lastseq + 1
            for wp in booking_id.waypoint_ids :
                after_insert_ids.append(wp.id)
        elif not self.able_to_deliver :
            # Not able to drop
            found = False
            insert_waypoint_id = self.pickup_id.id
            for wp in booking_id.waypoint_ids :
                if found : after_insert_ids.append(wp.id)
                elif wp.waypoint_id.id == insert_waypoint_id:
                    lastseq =  wp.sequence + 1
                    found = True
            wp_ids.append((0,0,{
                'sequence': lastseq,
                'waypoint_id': self.drop_id.id, 
                'drop_point': True,
                }))
            lastseq =  lastseq + 1

        for ID in after_insert_ids :
            wp_ids.append((1,ID,{'sequence': lastseq}))
            lastseq =  lastseq + 1
        
        booking_id.waypoint_ids=wp_ids
        booking_id.flush()
        booking_id.action_validate_route()


class FleetBookingWaypoint(models.Model):
    _name = "fleet.booking.waypoint" 
    _description = "Candidate Route Way point"
    _order = "sequence, booking_id"

    sequence = fields.Integer()
    booking_id = fields.Many2one(
        comodel_name="fleet.booking",
        string="Booking",
        required=True,
    )
    waypoint_id = fields.Many2one(
        comodel_name="res.partner",
        string="Stop Point",
        required=True,
    )
    pickup_point  = fields.Boolean(default=False)
    drop_point = fields.Boolean(default=False)

class FleetBookingTrip(models.Model):
    _name = "fleet.booking.trip" 
    _description = "Candidate Route Way trip"
    _order = "sequence "

    sequence = fields.Integer()
    booking_id = fields.Many2one(
        comodel_name="fleet.booking",
        string="Booking",
        required=True,
    )
    origin_id = fields.Many2one(
        comodel_name="res.partner",
        string="Origin",
        required=False,
    )
    #trip_origin_id = fields.Integer()
    destination_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination",
        required=False,
    )
    #trip_destination_id = fields.Integer()
    wp_origin_id = fields.Many2one(
        comodel_name="fleet.booking.waypoint",
        string="WP Origin",
        required=False,
    )
    wp_destination_id = fields.Many2one(
        comodel_name="fleet.booking.waypoint",
        string="WP Destination",
        required=False,
    )

    goods_ids = fields.One2many(
        comodel_name="fleet.booking.trip.goods",
        inverse_name="booking_trip_id",
        string="Package List",
    )
    
    pickup_trip = fields.Boolean("Pickup Trip")
    drop_trip = fields.Boolean('Drop Trip')

    # many2Many
class FleetBookingTrip(models.Model):
    _name = "fleet.booking.trip.goods" 
    _description = "Candidate Package / Goods per trip"
    _order = "sequence , booking_id, booking_trip_id"

    sequence = fields.Integer()

    booking_id = fields.Many2one(
        comodel_name="fleet.booking",
        string="Booking",
        required=True,
    )
    booking_trip_id = fields.Many2one(
        comodel_name="fleet.booking.trip",
        string="Booking Trip",
        required=True,
        ondelete='cascade',
    )

    booking_goods_id = fields.Many2one(
        comodel_name="fleet.booking.goods",
        string="Booking Trip Package",
        required=True,
    )

    booking_goods_dogs = fields.Char(
        "Description of Goods",
        related='booking_goods_id.dogs',
        store=False,copy=False, readonly=True)

    pickup_id = fields.Many2one(
        comodel_name="res.partner",
        string="Pickup",
        related='booking_goods_id.pickup_id',
        store=False,copy=False, readonly=True
    )
    # when null drop point is destination poi
    drop_id = fields.Many2one(
        comodel_name="res.partner",
        string="Drop",
        related='booking_goods_id.drop_id',
        store=False,copy=False, readonly=True
    )

    pickup_trip = fields.Boolean("Pickup This Trip")
    drop_trip = fields.Boolean('Drop This Trip')
    via_trip = fields.Boolean('Via This Trip')


    
 
    




 

